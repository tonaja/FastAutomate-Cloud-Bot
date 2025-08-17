import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import urlparse

from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    PageBreak, KeepTogether, Image, Frame, PageTemplate
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.pdfgen import canvas

from graph_state import GraphState
import google.generativeai as genai


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.logo_path = kwargs.pop('logo_path', 'assets/logo.png')
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        page_count = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_canvas(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_canvas(self, page_count):
        page_width, page_height = self._pagesize
        logo_width = 1.5 * inch
        logo_height = 0.5 * inch
        x = 0.5 * inch
        y = page_height - 0.5 * inch - logo_height  

        self.saveState()
        if self.logo_path and os.path.exists(self.logo_path):
            self.setFillColorRGB(1, 1, 1)
            self.rect(x, y, logo_width, logo_height, fill=1, stroke=0)
            self.drawImage(
                self.logo_path,
                x, y,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
        self.restoreState()

class ICPReportGenerator:
    def __init__(self, state: GraphState, company_name: str = None, website_url: str = None):
        self.company_name = self.extract_company_name(state.website_url or "https://company.com")
        self.styles = getSampleStyleSheet()
        self.logo_path = "assets/logo.png"
        self.setup_custom_styles()

    def extract_company_name(self, website_url: str) -> str:
        parsed = urlparse(website_url)
        domain = parsed.netloc

        if not domain:
            parsed = urlparse("https://" + website_url)
            domain = parsed.netloc

        domain = domain.replace("www.", "")
        company_name = domain.split(".")[0]
        company_name = re.sub(r'[^a-zA-Z0-9]', '', company_name)
        return company_name.lower()

    def setup_custom_styles(self):
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=16,
            spaceAfter=24,
            textColor=colors.black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            leading=20
        )
        
        self.section_heading_style = ParagraphStyle(
            'SectionHeading',
            fontSize=12,
            spaceAfter=10,
            spaceBefore=16,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            leftIndent=0,
            backColor=colors.white,
            borderPadding=4,
            alignment=TA_LEFT,
            wordWrap='LTR'
        )
        
        self.subsection_heading_style = ParagraphStyle(
            'SubsectionHeading',
            fontSize=11,
            spaceAfter=6,
            spaceBefore=10,
            textColor=colors.black,
            fontName='Helvetica-Bold',
            leftIndent=0
        )
        
        self.body_style = ParagraphStyle(
            'CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            leading=13
        )
        
        self.bullet_style = ParagraphStyle(
            'BulletStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            bulletIndent=10,
            spaceAfter=4,
            fontName='Helvetica',
            leading=13
        )
        
        self.table_header_style = ParagraphStyle(
            'TableHeader',
            fontSize=9,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            textColor=colors.black
        )
        
        self.table_cell_style = ParagraphStyle(
            'TableCell',
            fontSize=8,
            fontName='Helvetica',
            leading=10,
            alignment=TA_LEFT
        )

    def create_table_style(self):
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 1), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (0, -1), 8),
            ('FONTNAME', (1, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (1, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (1, 1), (-1, -1), colors.white),
        ])

    def format_cell_content(self, content: str) -> Paragraph:
        if not content:
            return Paragraph("", self.table_cell_style)
        
        if (',' in content or ';' in content) and len(content) > 50:
            delimiter = ',' if ',' in content else ';'
            items = [item.strip() for item in content.split(delimiter) if item.strip()]
            if len(items) > 1:
                formatted_content = '<br/>'.join([f"• {item}" for item in items])
                return Paragraph(formatted_content, self.table_cell_style)
        
        return Paragraph(content, self.table_cell_style)

    def create_b2b_icp_table(self, icp_data: Dict) -> Table:
        icp_profiles = icp_data.get('b2bICPTable', {}).get('icpProfiles', [])
        
        headers = ['DATA CATEGORY', 'SUB-FIELD', 'DESCRIPTION / WHAT TO FILL']
        for profile in icp_profiles:
            headers.append(f"ICP Name: {profile.get('name', 'Unnamed ICP')}")
        
        header_row = [Paragraph(h, self.table_header_style) for h in headers]
        table_data = [header_row]
        
        categories = [
            {
                'category': '1. Industry & Market',
                'fields': [
                    ('Industry Focus', 'Primary industry vertical (e.g., SaaS, Manufacturing, Finance).'),
                    ('Key Market Trends', 'Emerging or ongoing trends (cloud adoption, automation, regulatory changes).'),
                    ('Market Maturity', 'Whether the market is emerging, mature, or highly competitive.')
                ]
            },
            {
                'category': '2. Firmographics',
                'fields': [
                    ('Employee Count Range', 'Approximate range (e.g., 50–500, 501–5,000).'),
                    ('Annual Revenue Range', 'Typical revenue bracket ($5M–$50M, $50M–$500M).'),
                    ('Geographic Focus / HQ Location', 'Region(s) in which they operate or have the largest presence.'),
                    ('Funding Stage (if relevant)', 'Pre-seed, Series A, IPO, or Bootstrapped.')
                ]
            },
            {
                'category': '3. Decision-Maker Titles & Roles',
                'fields': [
                    ('Primary Decision-Maker(s)', 'The job titles most likely to sign off on the purchase (CEO, CTO, CFO, etc.).'),
                    ('Influencers & Champions', 'Roles that significantly influence the buying decision (team leads, department heads).'),
                    ('Buying Committee Structure', 'Whether one person decides, or a formal committee/board is involved.')
                ]
            },
            {
                'category': '4. Business Objectives & Challenges',
                'fields': [
                    ('Common Growth Objectives', 'Goals such as expanding into new markets, cost reduction, or digital transformation.'),
                    ('Key Pain Points', 'Typical operational or strategic challenges (e.g., compliance, scaling infrastructure).')
                ]
            },
            {
                'category': '5. Value Alignment',
                'fields': [
                    ('Feature-Need Match', 'Specific ways your product/service addresses these challenges or objectives.'),
                    ('ROI Potential', 'Likely impact on revenue, cost savings, or process efficiency.')
                ]
            },
            {
                'category': '6. Best-Fit Indicators',
                'fields': [
                    ('Growth-Related Triggers', 'Signals of readiness (recent funding, acquisitions, reorgs, etc.).'),
                    ('Cultural or Tech Stack Synergy', 'Shared values or compatible technologies that support faster adoption.'),
                    ('Other Unique Clues', 'Awards, brand reputation, or known strategic initiatives that align with your offering.')
                ]
            }
        ]

        for category in categories:
            category_name = category['category']
            fields = category['fields']
            
            for field_idx, (field_name, description) in enumerate(fields):
                row = []
                
                if field_idx == 0:
                    row.append(Paragraph(category_name, self.table_cell_style))
                else:
                    row.append(Paragraph("", self.table_cell_style))
                
                row.append(Paragraph(field_name, self.table_cell_style))
                row.append(Paragraph(description, self.table_cell_style))
                
                for profile in icp_profiles:
                    profile_data = profile.get('data', {})
                    field_key = field_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('-', '_')
                    
                    value = (profile_data.get(field_key, '') or 
                            profile_data.get(field_key.replace('__', '_'), '') or
                            profile_data.get(field_name.lower().replace(' ', '_'), ''))
                    
                    row.append(self.format_cell_content(str(value)))
                
                table_data.append(row)

        col_widths = [1.2*inch, 1.8*inch, 2.2*inch]
        if icp_profiles:
            remaining_width = 10.5*inch - sum(col_widths)
            icp_col_width = remaining_width / len(icp_profiles)
            col_widths.extend([icp_col_width] * len(icp_profiles))

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self.create_table_style())
        
        return table

    def create_buyer_personas_table(self, icp_data: Dict) -> Table:
        personas = icp_data.get('buyerPersonasTable', {}).get('personas', [])
        
        headers = ['DATA CATEGORY', 'SUB-FIELD']
        for persona in personas:
            headers.append(f"Persona Name: {persona.get('name', 'Unnamed Persona')}")
        
        header_row = [Paragraph(h, self.table_header_style) for h in headers]
        table_data = [header_row]
        
        categories = [
            {
                'category': '1. Goals & Motivations',
                'fields': [
                    ('Primary Objectives', ''),
                    ('Success Metrics', '')
                ]
            },
            {
                'category': '2. Preferred Channels & Content',
                'fields': [
                    ('Research Sources', ''),
                    ('Content Formats', '')
                ]
            },
            {
                'category': '3. Key Objections',
                'fields': [
                    ('Reasons to Hesitate', '')
                ]
            },
            {
                'category': '4. Messaging / Value Prop Focus',
                'fields': [
                    ('Tailored Hooks', '')
                ]
            }
        ]

        for category in categories:
            category_name = category['category']
            fields = category['fields']
            
            for field_idx, (field_name, _) in enumerate(fields):
                row = []
                
                if field_idx == 0:
                    row.append(Paragraph(category_name, self.table_cell_style))
                else:
                    row.append(Paragraph("", self.table_cell_style))
                
                row.append(Paragraph(field_name, self.table_cell_style))
                
                for persona in personas:
                    persona_data = persona.get('data', {})
                    field_key = field_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('-', '_')
                    
                    value = (persona_data.get(field_key, '') or 
                            persona_data.get(field_key.replace('__', '_'), '') or
                            persona_data.get(field_name.lower().replace(' ', '_'), ''))
                    
                    row.append(self.format_cell_content(str(value)))
                
                table_data.append(row)

        col_widths = [1.2*inch, 2*inch]
        if personas:
            remaining_width = 10.5*inch - sum(col_widths)
            persona_col_width = remaining_width / len(personas)
            col_widths.extend([persona_col_width] * len(personas))

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self.create_table_style())
        
        return table

    def generate_pdf_report(self, icp_data: Dict, output_path: str = None) -> str:
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_company_name = re.sub(r'[<>:"/\\|?*]', '', self.company_name)
            output_path = f'outputs/{clean_company_name}_Ideal_Customer_Buyer_Persona_Profiles_Report_ICPs.pdf'

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=landscape(letter),
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=1*inch,
            bottomMargin=0.6*inch
        )
        
        story = []
        
        title_text = f'<b>"{self.company_name}" Ideal Customer & Buyer Persona Profiles Report (ICPs)</b>'
        title = Paragraph(title_text, self.title_style)
        story.append(title)
        story.append(Spacer(1, 24))
        
        def create_section_heading(text):
            heading_paragraph = Paragraph(f'<b>{text}</b>', self.section_heading_style)
            return KeepTogether([heading_paragraph])
        
        story.append(create_section_heading('1. Introduction'))
        story.append(Spacer(1, 10))
        
        story.append(Paragraph('<b>Purpose & Audience</b>', self.subsection_heading_style))
        purpose_text = f"""This framework is designed for {self.company_name} to pinpoint its ideal business customers (B2B) within the Egyptian transportation 
segment and define the key individuals within those organizations (Buyer Personas). By documenting who to target and why, 
{self.company_name}'s Marketing and Sales teams can:"""
        story.append(Paragraph(purpose_text, self.body_style))
        story.append(Spacer(1, 6))
        
        bullet_points = [
            f"Craft targeted marketing campaigns that resonate with each segment's specific needs related to employee and organizational transportation.",
            f"Allocate resources efficiently by focusing on best-fit leads and high-value opportunities within the transportation sector in Egypt.",
            f"Refine service offerings and messaging to address the most pressing pain points of ideal transportation-focused customers in the Egyptian market."
        ]
        
        for point in bullet_points:
            story.append(Paragraph(f"• {point}", self.bullet_style))
        
        story.append(Spacer(1, 12))
        
        story.append(Paragraph('<b>Key Terms</b>', self.subsection_heading_style))
        story.append(Paragraph(f"• <b>ICP (Ideal Customer Profile):</b> Describes the type of company within the transportation segment in Egypt that would benefit most from {self.company_name}'s offerings.", self.bullet_style))
        story.append(Paragraph("• <b>Buyer Persona:</b> A semi-fictional individual within the ICP—such as a decision-maker or influencer in HR, Admin, Fleet, or Facility Management—whose needs, motivations, and objections must be understood to drive engagement and contract closure.", self.bullet_style))
        
        story.append(PageBreak())
        
        story.append(create_section_heading('2. B2B ICP'))
        story.append(Spacer(1, 10))
        
        b2b_table = self.create_b2b_icp_table(icp_data)
        story.append(b2b_table)
        story.append(PageBreak())
        
        story.append(create_section_heading('4. Buyer Personas Table'))
        story.append(Spacer(1, 10))
        
        personas_table = self.create_buyer_personas_table(icp_data)
        story.append(personas_table)
        
        doc.build(story, canvasmaker=lambda *args, **kwargs: NumberedCanvas(*args, logo_path=self.logo_path, **kwargs))
        print(f"🎯 PDF report generated: {output_path}")
        
        return output_path


def generate_icp_with_gemini(growth_report: Dict, company_name: str, max_retries: int = 2) -> Dict:
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables")
        return create_fallback_icp_data(company_name)
    
    genai.configure(api_key=api_key)
    
    prompt_template = """Act as a senior strategy consultant and digital growth analyst. You MUST return a complete, valid JSON object with exactly 4 ICP profiles and 4-5 buyer personas. 

CRITICAL: Your response must be ONLY valid JSON - no additional text, explanations, or markdown formatting.

Company Name: {company_name}
Growth Report Data: {growth_report}

Generate exactly this JSON structure (complete all fields with specific content):

{{
  "b2bICPTable": {{
    "icpProfiles": [
      {{
        "name": "Large Manufacturing Companies (Industrial Cities)",
        "data": {{
          "industry_focus": "Manufacturing, Automotive, Pharmaceuticals",
          "key_market_trends": "Industrial automation, Supply chain digitization, Workforce retention challenges",
          "market_maturity": "Mature market with high competition",
          "employee_count_range": "500-5,000 employees",
          "annual_revenue_range": "$10M-$200M annually",
          "geographic_focus_hq_location": "6th of October City, 10th of Ramadan City, Alexandria Industrial Zone",
          "funding_stage_if_relevant": "Established businesses with international partnerships",
          "primary_decision_makers": "CEO, HR Director, Operations Manager",
          "influencers_champions": "Plant Managers, Safety Officers, Employee Representatives",
          "buying_committee_structure": "Committee-based decisions involving HR, Operations, Finance",
          "common_growth_objectives": "Improve employee retention, Reduce operational costs, Enhance workplace safety",
          "key_pain_points": "High employee turnover, Transportation-related absenteeism, Rising commute costs",
          "feature_need_match": "Reliable shuttle services, Shift-based transportation, Safety tracking systems",
          "roi_potential": "20-30% reduction in turnover costs, 15% improvement in punctuality",
          "growth_related_triggers": "New plant openings, Expansion of workforce, Compliance requirements",
          "cultural_or_tech_stack_synergy": "Focus on employee welfare, Technology-forward operations, Safety-first culture",
          "other_unique_clues": "ISO certifications, International partnerships, Sustainability initiatives"
        }}
      }},
      {{
        "name": "Commercial Banks & Financial Institutions",
        "data": {{
          "industry_focus": "Banking, Financial Services, Insurance",
          "key_market_trends": "Digital transformation, Employee experience focus, Cost optimization",
          "market_maturity": "Highly competitive mature market",
          "employee_count_range": "200-2,000 employees",
          "annual_revenue_range": "$5M-$100M annually",
          "geographic_focus_hq_location": "New Administrative Capital, Cairo Business District, Alexandria",
          "funding_stage_if_relevant": "Established institutions, publicly traded",
          "primary_decision_makers": "COO, HR Director, Facilities Manager",
          "influencers_champions": "Branch Managers, Employee Relations Team, Union Representatives",
          "buying_committee_structure": "Formal procurement committee with multiple approvals",
          "common_growth_objectives": "Enhance employee satisfaction, Reduce operational expenses, Improve service quality",
          "key_pain_points": "High commuting stress, Parking limitations, Employee transport complaints",
          "feature_need_match": "Executive transportation, Scheduled shuttles, Flexible routing",
          "roi_potential": "25% reduction in transport allowances, Improved employee satisfaction",
          "growth_related_triggers": "New branch openings, HQ relocation, Employee retention initiatives",
          "cultural_or_tech_stack_synergy": "Professional service standards, Technology integration, CSR focus",
          "other_unique_clues": "Corporate certifications, Sustainability reporting, Employee welfare programs"
        }}
      }},
      {{
        "name": "Educational Institutions & Universities",
        "data": {{
          "industry_focus": "Private Universities, International Schools, Training Centers",
          "key_market_trends": "Student safety prioritization, Campus expansion, International accreditation",
          "market_maturity": "Growing market with increasing competition",
          "employee_count_range": "100-1,500 employees",
          "annual_revenue_range": "$2M-$50M annually",
          "geographic_focus_hq_location": "New Cairo, 6th of October City, Sheikh Zayed, Alexandria",
          "funding_stage_if_relevant": "Mix of private ownership and international partnerships",
          "primary_decision_makers": "University President, Operations Director, Student Affairs Director",
          "influencers_champions": "Transportation Committee, Student Union, Parent Associations",
          "buying_committee_structure": "Academic committee with administrative approval",
          "common_growth_objectives": "Ensure student safety, Improve service quality, Enhance reputation",
          "key_pain_points": "Student safety concerns, Irregular transport, Parent complaints",
          "feature_need_match": "Safe student transportation, Reliable scheduling, GPS tracking",
          "roi_potential": "Enhanced reputation, Reduced liability, Improved parent satisfaction",
          "growth_related_triggers": "New campus development, Enrollment growth, Safety incidents",
          "cultural_or_tech_stack_synergy": "Safety-first mentality, Technology integration, Community focus",
          "other_unique_clues": "International accreditations, Safety awards, Community programs"
        }}
      }},
      {{
        "name": "Healthcare & Medical Facilities",
        "data": {{
          "industry_focus": "Private Hospitals, Medical Centers, Pharmaceutical Companies",
          "key_market_trends": "Healthcare digitization, Staff retention challenges, 24/7 operations",
          "market_maturity": "Mature market with high service standards",
          "employee_count_range": "150-3,000 employees",
          "annual_revenue_range": "$3M-$150M annually",
          "geographic_focus_hq_location": "New Administrative Capital, Cairo Medical City, Alexandria",
          "funding_stage_if_relevant": "Established institutions with international partnerships",
          "primary_decision_makers": "Hospital Administrator, HR Director, Operations Manager",
          "influencers_champions": "Department Heads, Nursing Supervisors, Medical Staff Representatives",
          "buying_committee_structure": "Medical board and administrative committee approval",
          "common_growth_objectives": "Ensure staff availability, Improve employee satisfaction, Maintain continuity",
          "key_pain_points": "Staff absenteeism, Night shift transport challenges, High nursing turnover",
          "feature_need_match": "24/7 transportation, Emergency call systems, Shift-based scheduling",
          "roi_potential": "Reduced turnover costs, Improved continuity, Enhanced staff satisfaction",
          "growth_related_triggers": "New facility openings, Service expansion, Staff shortages",
          "cultural_or_tech_stack_synergy": "Healthcare excellence, Safety focus, Technology adoption",
          "other_unique_clues": "Medical accreditations, Healthcare awards, Staff retention programs"
        }}
      }}
    ]
  }},
  "buyerPersonasTable": {{
    "personas": [
      {{
        "name": "Ahmed (HR Director)",
        "data": {{
          "primary_objectives": "Reduce employee turnover, Improve staff satisfaction, Manage transport costs",
          "success_metrics": "Turnover rate reduction, Employee satisfaction scores, Cost per employee",
          "fears_frustrations": "High turnover, Budget constraints, Safety incidents, Vendor reliability",
          "research_sources": "HR associations, LinkedIn networks, HR conferences, Peer recommendations",
          "content_formats": "Case studies with ROI data, Industry reports, Webinars, Testimonials",
          "reasons_to_hesitate": "Budget approval processes, Previous bad experiences, Service reliability concerns",
          "tailored_hooks": "Proven ROI in retention, Comprehensive safety standards, Flexible packages"
        }}
      }},
      {{
        "name": "Fatma (Operations Manager)",
        "data": {{
          "primary_objectives": "Ensure operational continuity, Optimize resources, Maintain quality standards",
          "success_metrics": "Service uptime percentage, Employee punctuality, Operational efficiency",
          "fears_frustrations": "Service disruptions, Coordination complexity, Quality control challenges",
          "research_sources": "Operations forums, Best practices guides, Vendor platforms, Professional networks",
          "content_formats": "Technical specifications, Implementation timelines, Process guides, Dashboards",
          "reasons_to_hesitate": "Integration complexity, Change management concerns, Performance guarantees",
          "tailored_hooks": "Seamless integration, Real-time monitoring, Dedicated account management"
        }}
      }},
      {{
        "name": "Hassan (CFO)",
        "data": {{
          "primary_objectives": "Control operational costs, Maximize ROI, Ensure budget compliance",
          "success_metrics": "Cost reduction percentages, ROI calculations, Budget variance analysis",
          "fears_frustrations": "Cost overruns, Poor ROI performance, Complex pricing, Long-term risks",
          "research_sources": "Financial reports, Benchmarking studies, CFO networks, Financial publications",
          "content_formats": "Cost-benefit analyses, ROI calculators, Financial case studies, Benchmarks",
          "reasons_to_hesitate": "High upfront investments, Unclear ROI projections, Contract inflexibility",
          "tailored_hooks": "Clear ROI projections, Flexible pricing models, Cost transparency"
        }}
      }},
      {{
        "name": "Mariam (Facilities Manager)",
        "data": {{
          "primary_objectives": "Ensure employee safety, Manage operations efficiently, Coordinate services",
          "success_metrics": "Safety incident rates, Service quality ratings, Employee feedback scores",
          "fears_frustrations": "Safety concerns, Service coordination challenges, Quality control issues",
          "research_sources": "Facilities associations, Safety forums, Industry publications, Conferences",
          "content_formats": "Safety protocols, Service standards, Implementation guides, Best practices",
          "reasons_to_hesitate": "Safety compliance, Coordination complexity, Quality assurance concerns",
          "tailored_hooks": "Comprehensive safety standards, 24/7 support, Quality assurance programs"
        }}
      }}
    ]
  }}
}}"""

    for attempt in range(max_retries + 1):
        try:
            model = genai.GenerativeModel('gemini-2.5-pro')
            
            generation_config = genai.GenerationConfig(
                temperature=0.2,
                max_output_tokens=16384,
                response_mime_type="application/json"
            )
            
            full_prompt = prompt_template.format(
                company_name=company_name,
                growth_report=json.dumps(growth_report, indent=2)
            )
            
            response = model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            response_text = response.text.strip()
            
            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1]
                
                response_text = response_text.strip()
                
                import re
                response_text = re.sub(r',\s*}', '}', response_text)
                response_text = re.sub(r',\s*]', ']', response_text)
                
                if response_text.count('{') != response_text.count('}'):
                    open_braces = 0
                    last_valid_pos = -1
                    for i, char in enumerate(response_text):
                        if char == '{':
                            open_braces += 1
                        elif char == '}':
                            open_braces -= 1
                            if open_braces == 0:
                                last_valid_pos = i
                                break
                    
                    if last_valid_pos > -1:
                        response_text = response_text[:last_valid_pos + 1]
                
                icp_data = json.loads(response_text)
                
                if not isinstance(icp_data, dict):
                    raise ValueError("Response is not a dictionary")
                
                if "b2bICPTable" not in icp_data or "buyerPersonasTable" not in icp_data:
                    raise ValueError("Missing required sections in response")
                
                icp_profiles = icp_data.get('b2bICPTable', {}).get('icpProfiles', [])
                personas = icp_data.get('buyerPersonasTable', {}).get('personas', [])
                
                return icp_data
                
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    continue
                else:
                    debug_path = f"outputs/debug_gemini_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    try:
                        with open(debug_path, 'w', encoding='utf-8') as f:
                            f.write(response_text)
                    except Exception:
                        pass
                    
                    return create_fallback_icp_data(company_name)
                
        except Exception as e:
            if attempt < max_retries:
                continue
            else:
                return create_fallback_icp_data(company_name)
    
    return create_fallback_icp_data(company_name)


def create_fallback_icp_data(company_name: str) -> Dict:
    return {
        "b2bICPTable": {
            "icpProfiles": [
                {
                    "name": "Large Enterprises (Corporate Sector)",
                    "data": {
                        "industry_focus": f"Large corporations in Egypt requiring {company_name.lower()} services",
                        "key_market_trends": "Digital transformation, Employee experience focus, Cost optimization",
                        "market_maturity": "Mature market with established players",
                        "employee_count_range": "500+ employees",
                        "annual_revenue_range": "$10M+ annually",
                        "geographic_focus_hq_location": "Cairo, Alexandria, New Administrative Capital",
                        "funding_stage_if_relevant": "Established businesses",
                        "primary_decision_makers": "CEO, Operations Director, HR Director",
                        "influencers_champions": "Department heads, Team leaders",
                        "buying_committee_structure": "Committee-based decision making",
                        "common_growth_objectives": "Improve efficiency, Reduce costs, Enhance employee satisfaction",
                        "key_pain_points": "Operational inefficiencies, Rising costs, Employee retention",
                        "feature_need_match": f"Services that address operational challenges specific to {company_name.lower()}",
                        "roi_potential": "Cost savings and efficiency improvements",
                        "growth_related_triggers": "Business expansion, Operational challenges",
                        "cultural_or_tech_stack_synergy": "Technology-forward, Efficiency-focused",
                        "other_unique_clues": "Industry certifications, Growth initiatives"
                    }
                }
            ]
        },
        "buyerPersonasTable": {
            "personas": [
                {
                    "name": "Ahmed (Decision Maker)",
                    "data": {
                        "primary_objectives": "Improve business operations, Manage costs, Drive growth",
                        "success_metrics": "ROI, Cost reduction, Operational efficiency",
                        "fears_frustrations": "Budget constraints, Poor vendor performance, Implementation risks",
                        "research_sources": "Industry publications, Professional networks, Online research",
                        "content_formats": "Case studies, ROI analyses, Industry reports",
                        "reasons_to_hesitate": "Budget approval, Risk concerns, Past experiences",
                        "tailored_hooks": "Proven ROI, Risk mitigation, Industry expertise"
                    }
                }
            ]
        }
    }

def icp_generator_node(state: GraphState) -> GraphState:
   
   
    try:
        growth_report = state.GR_JSON
        website_url = state.website_url
        
        if not growth_report:
            logger.warning("No growth report found from Node A")
            return state
        
        company_name = growth_report.get('company_name', 'Company')
        if not company_name or company_name == 'Company':
            if website_url:
                from urllib.parse import urlparse
                parsed_url = urlparse(website_url if website_url.startswith('http') else f'https://{website_url}')
                domain = parsed_url.netloc or parsed_url.path
                company_name = domain.replace('www.', '').split('.')[0].title() if domain else 'Company'
        
        icp_data = generate_icp_with_gemini(growth_report, company_name, max_retries=2)
        
        icp_profiles = icp_data.get('b2bICPTable', {}).get('icpProfiles', [])
        personas = icp_data.get('buyerPersonasTable', {}).get('personas', [])
        
        report_generator = ICPReportGenerator(state, company_name)
        pdf_path = report_generator.generate_pdf_report(icp_data)
        
        state.ICP_GENERATOR_JSON = {
            **icp_data,
            "pdf_report_path": pdf_path,
            "generation_timestamp": datetime.now().isoformat(),
            "company_name": company_name,
            "model_used": "gemini-2.5-pro"
        }
        
        return state
        
    except Exception as e:
        logger.error(f"❌ Error in ICP Generator Node: {e}")
        import traceback
        traceback.print_exc()
        return state