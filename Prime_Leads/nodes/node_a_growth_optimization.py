import os
import json
from pathlib import Path
from fpdf import FPDF
import google.generativeai as genai
from datetime import datetime
import re
from graph_state import GraphState

class DynamicGrowthReportPDF(FPDF):
    def __init__(self, company_name: str, **kwargs):
        super().__init__(**kwargs)
        self.company_name = company_name
        self.set_auto_page_break(auto=True, margin=15)
        self.font_name = "Arial"
        self.set_font("Arial", size=11)
        self.logo_path = "assets/logo.png"
        
    def header(self):
        if self.page_no() == 1:
            return
            
        if os.path.exists(self.logo_path) and self.page_no() > 1:
            try:
                self.image(self.logo_path, 10, 8, 30)
            except Exception:
                pass
        
        self.ln(20)
    
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
    
    def add_section_header(self, section_num: int, title: str):
        self.set_fill_color(255, 255, 153)
        self.set_text_color(0, 0, 0)
        self.set_font("Arial", style='B', size=12)
        self.ln(5)
        
        section_text = f"{section_num}. {title}"
        text_width = self.get_string_width(section_text) + 6
        self.cell(text_width, 10, section_text, fill=True)
        self.ln(12)
        self.set_text_color(0, 0, 0)
    
    def _clean_text_for_pdf(self, text: str) -> str:
        if not text:
            return ""
        
        replacements = {
            '\u2022': '-',
            '\u25e6': '*',
            '\u2013': '-',
            '\u2014': '--',
            '\u201c': '"',
            '\u201d': '"',
            '\u2018': "'",
            '\u2019': "'",
            '\u2026': '...',
            '\u00a0': ' ',
        }
        
        for unicode_char, ascii_char in replacements.items():
            text = text.replace(unicode_char, ascii_char)
        
        try:
            text.encode('latin-1')
            return text
        except UnicodeEncodeError:
            return text.encode('ascii', errors='ignore').decode('ascii')
    
    def add_bullet_point(self, text: str, level: int = 0):
        indent = 15 + (level * 10)
        bullet = "-" if level == 0 else "*"
        
        self.set_x(indent)
        self.set_font("Arial", size=11)
        
        current_x = self.get_x()
        self.cell(5, 6, bullet)
        self.set_x(current_x + 8)
        
        clean_text = self._clean_text_for_pdf(text)
        self.multi_cell(190 - indent - 8, 6, clean_text)
        self.ln(1)
    
    def add_subsection(self, title: str, content):
        self.set_font("Arial", style='B', size=11)
        clean_title = self._clean_text_for_pdf(str(title))
        self.cell(0, 8, f"{clean_title}:")
        self.ln(8)
        
        self.set_font("Arial", size=11)
        if isinstance(content, list):
            for item in content:
                clean_item = self._clean_text_for_pdf(str(item))
                self.add_bullet_point(clean_item, level=1)
        elif isinstance(content, dict):
            for key, value in content.items():
                clean_key = self._clean_text_for_pdf(str(key))
                clean_value = self._clean_text_for_pdf(str(value))
                self.add_bullet_point(f"{clean_key}: {clean_value}", level=1)
        else:
            clean_content = self._clean_text_for_pdf(str(content))
            self.add_bullet_point(clean_content, level=1)
        
        self.ln(3)

    def check_page_break(self, space_needed: int = 30):
        if self.get_y() + space_needed > 280:
            self.add_page()
    
    def _extract_key_message(self, text: str, max_words: int = 10) -> str:
        if not text or text == "Not specified":
            return "N/A"
        
        clean_text = self._clean_text_for_pdf(str(text))
        words = clean_text.split()
        
        if len(words) <= max_words:
            return clean_text
        
        key_terms = []
        important_words = []
        
        business_keywords = {
            'platform', 'technology', 'delivery', 'service', 'market', 'customer', 
            'analytics', 'optimization', 'integration', 'automation', 'digital',
            'enterprise', 'solution', 'innovation', 'efficiency', 'competitive',
            'advantage', 'leadership', 'quality', 'safety', 'customization'
        }
        
        for word in words:
            word_lower = word.lower().strip('.,!?":;')
            if word_lower in business_keywords or len(word) > 6:
                important_words.append(word)
        
        result_words = words[:4]
        
        for word in important_words[:6]:
            if len(result_words) < max_words and word not in result_words:
                result_words.append(word)
        
        result = " ".join(result_words[:max_words])
        return result
    
    def _create_ultra_concise_table(self, competitors_data: list):
        if not competitors_data:
            return
        
        self.check_page_break(50)
        
        start_x = 8
        feature_col_width = 32
        competitors = competitors_data[:3]
        comp_col_width = (187 - feature_col_width) / len(competitors)
        
        key_features = [
            "Core Offering",
            "Technology Focus", 
            "Target Market",
            "Competitive Advantage",
            "Strengths",
            "Weaknesses"
        ]
        
        self.set_fill_color(240, 240, 240)
        self.set_font("Arial", style='B', size=9)
        
        self.set_xy(start_x, self.get_y())
        self.cell(feature_col_width, 10, 'Feature', border=1, align='C', fill=True)
        
        current_x = start_x + feature_col_width
        for comp in competitors:
            comp_name = self._extract_key_message(comp.get('Competitor', 'Unknown'), 2)
            self.set_xy(current_x, self.get_y())
            self.cell(comp_col_width, 10, comp_name, border=1, align='C', fill=True)
            current_x += comp_col_width
        
        self.ln(10)
        
        row_height = 25
        
        for feature in key_features:
            current_y = self.get_y()
            
            if current_y > 230:
                self.add_page()
                self._recreate_concise_header(competitors, start_x, feature_col_width, comp_col_width)
                current_y = self.get_y()
            
            row_contents = []
            for comp in competitors:
                content = self._get_meaningful_content(comp, feature)
                concise_content = self._extract_key_message(content, 10)
                row_contents.append(concise_content)
            
            self.set_fill_color(240, 240, 240)
            self.set_xy(start_x, current_y)
            self.cell(feature_col_width, row_height, '', border=1, fill=True)
            
            self.set_xy(start_x + 2, current_y + 3)
            self.set_font("Arial", style='B', size=8)
            self._draw_smart_text(feature, feature_col_width - 4, row_height - 6)
            
            self.set_fill_color(255, 255, 255)
            current_x = start_x + feature_col_width
            
            for content_text in row_contents:
                self.set_xy(current_x, current_y)
                self.cell(comp_col_width, row_height, '', border=1)
                
                self.set_xy(current_x + 2, current_y + 3)
                self.set_font("Arial", size=7)
                self._draw_smart_text(content_text, comp_col_width - 4, row_height - 6)
                
                current_x += comp_col_width
            
            self.set_xy(start_x, current_y + row_height)
        
        self.ln(10)
    
    def _draw_smart_text(self, text: str, max_width: float, max_height: float):
        if not text:
            return
        
        words = text.split()
        lines = []
        current_line = ""
        
        if len(words) <= 6:
            words_per_line = 3
        else:
            words_per_line = 4
        
        for i in range(0, len(words), words_per_line):
            line = " ".join(words[i:i + words_per_line])
            lines.append(line)
        
        line_height = 3.5
        start_x = self.get_x()
        start_y = self.get_y()
        
        for i, line in enumerate(lines[:5]):
            if i * line_height < max_height - line_height:
                self.set_xy(start_x, start_y + (i * line_height))
                self.cell(max_width, line_height, line)
    
    def _recreate_concise_header(self, competitors, start_x, feature_col_width, comp_col_width):
        self.set_fill_color(255, 255, 153)
        self.set_font("Arial", style='B', size=9)
        
        self.set_xy(start_x, self.get_y())
        self.cell(feature_col_width, 10, 'Feature', border=1, align='C', fill=True)
        
        current_x = start_x + feature_col_width
        for comp in competitors:
            comp_name = self._extract_key_message(comp.get('Competitor', 'Unknown'), 2)
            self.set_xy(current_x, self.get_y())
            self.cell(comp_col_width, 10, comp_name, border=1, align='C', fill=True)
            current_x += comp_col_width
        
        self.ln(10)

    def _get_meaningful_content(self, competitor: dict, feature: str):
        content_map = {
            "Core Offering": competitor.get("Core Offering", "Service delivery platform"),
            "Technology Focus": competitor.get("Technology Focus", "Digital platform technology"),
            "Target Market": competitor.get("Target Market", "Urban consumers"),
            "Competitive Advantage": competitor.get("Competitive Advantage", "Market positioning"),
            "Strengths": self._extract_first_strength(competitor.get("Strengths", [])),
            "Weaknesses": self._extract_first_weakness(competitor.get("Weaknesses", []))
        }
        
        content = content_map.get(feature, "Standard approach")
        
        if isinstance(content, list) and content:
            content = content[0]
        
        return str(content)
    
    def _extract_first_strength(self, strengths):
        if isinstance(strengths, list) and strengths:
            return strengths[0]
        return str(strengths) if strengths else "Market presence"
    
    def _extract_first_weakness(self, weaknesses):
        if isinstance(weaknesses, list) and weaknesses:
            return weaknesses[0]
        return str(weaknesses) if weaknesses else "Limited data"


class GrowthReportGenerator:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-pro") 
        
        os.makedirs("outputs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("prompts", exist_ok=True)
    
    def load_website_url(self) -> str:
        url_file_path = "data/sample_website_url.txt"
        
        if not os.path.exists(url_file_path):
            raise FileNotFoundError(f"Website URL file not found: {url_file_path}")
        
        with open(url_file_path, 'r', encoding='utf-8') as f:
            website_url = f.read().strip()
        
        if not website_url:
            raise ValueError("Website URL file is empty")
        
        if not website_url.startswith(("http://", "https://")):
            website_url = "https://" + website_url
        
        return website_url
    
    def load_prompt_template(self) -> str:
        prompt_file_path = "prompts/growth_optimization_report.txt"
        
        if not os.path.exists(prompt_file_path):
            raise FileNotFoundError(f"Prompt template file not found: {prompt_file_path}")
        
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read().strip()
        
        if not prompt_template:
            raise ValueError("Prompt template file is empty")
        
        return prompt_template
    
    def extract_company_name(self, website_url: str) -> str:
        clean_url = website_url.replace("https://", "").replace("http://", "").replace("www.", "")
        domain_parts = clean_url.split('/')[0].split('.')
        company_name = domain_parts[0]
        company_name = re.sub(r'[^a-zA-Z0-9]', '', company_name)
        company_name = company_name.capitalize()
        return company_name
    
    def generate_report_content(self, website_url: str, prompt_template: str) -> dict:
        safe_prompt_template = prompt_template.replace("WEBSITE_URL_PLACEHOLDER", website_url)
        if "{website_url}" in safe_prompt_template:
            safe_prompt_template = safe_prompt_template.replace("{website_url}", website_url)
        
        enhanced_prompt = f"""
{safe_prompt_template}

SPECIAL INSTRUCTION FOR COMPETITIVE ANALYSIS:
For the "Top Competitor Comparison Table" section, each cell should contain the ESSENCE of the information in 10 words or less, but capture the FULL MEANING. Focus on:

1. Core differentiators, not generic descriptions
2. Specific advantages, not vague statements  
3. Concrete weaknesses, not diplomatic language
4. Actual technology focus, not buzzwords

Examples of GOOD concise content that preserves full meaning:
- Core Offering: "AI-powered multi-category delivery with grocery focus"
- Technology Focus: "Machine learning logistics optimization and routing"
- Strengths: "Market dominance through scale and partnerships"
- Weaknesses: "High costs eroding profitability margins"

The goal is MEANINGFUL BREVITY - every word should add value.

CRITICAL: Your response MUST be ONLY valid JSON. No markdown, no explanations, just JSON.
"""
        
        try:
            response = self.model.generate_content(
                enhanced_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    top_p=0.9,
                    top_k=40,
                    max_output_tokens=8192,
                )
            )
            
            if not response or not response.text:
                return self._create_enhanced_fallback_report(website_url)
            
            content = response.text.strip()
            
            try:
                with open(f"outputs/raw_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w', encoding='utf-8') as f:
                    f.write(content)
            except:
                pass
            
            content_cleaned = self._simple_json_cleaning(content)
            parsed_data = self._safe_json_parse(content_cleaned)
            
            if not parsed_data:
                return self._create_enhanced_fallback_report(website_url)
            
            if not self._validate_report_structure(parsed_data):
                parsed_data = self._enhance_with_fallback(parsed_data, website_url)
            
            return parsed_data
            
        except Exception as e:
            return self._create_enhanced_fallback_report(website_url)
    
    def _simple_json_cleaning(self, content: str) -> str:
        content = content.strip()
        
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            raise ValueError("No valid JSON found in response")
        
        json_content = content[start_idx:end_idx + 1]
        
        try:
            json.loads(json_content)
            return json_content
        except json.JSONDecodeError as e:
            brace_count = 0
            for i, char in enumerate(content[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        better_content = content[start_idx:i + 1]
                        try:
                            json.loads(better_content)
                            return better_content
                        except:
                            continue
            
            return json_content
    
    def _safe_json_parse(self, content: str) -> dict:
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            fixes = [
                lambda x: re.sub(r',(\s*[}\]])', r'\1', x),
                lambda x: x.replace('\\"', '"').replace('"', '\\"').replace('\\"', '"', 1),
            ]
            
            for fix in fixes:
                try:
                    fixed_content = fix(content)
                    result = json.loads(fixed_content)
                    return result
                except:
                    continue
            
            return None
    
    def _validate_report_structure(self, data: dict) -> bool:
        required_keys = [
            "Introduction",
            "Company Offerings & Value Propositions",
            "Competitive Review and Comparison"
        ]
        
        for key in required_keys:
            if key not in data:
                return False
        
        return True
    
    def _enhance_with_fallback(self, data: dict, website_url: str) -> dict:
        fallback = self._create_enhanced_fallback_report(website_url)
        
        for key, value in fallback.items():
            if key not in data or not data[key]:
                data[key] = value
        
        return data
    
    def _create_enhanced_fallback_report(self, website_url: str) -> dict:
        company_name = self.extract_company_name(website_url)
        
        return {
            "Introduction": f"Strategic growth analysis for {company_name} examining market position, competitive landscape, and optimization opportunities.",
            
            "Company Offerings & Value Propositions": {
                "Core Offerings & Claimed Pain Points": f"{company_name} service analysis focusing on value proposition and customer pain point resolution.",
                "Market Fit & Differentiation": f"Market positioning assessment for {company_name} with competitive differentiation strategy review."
            },
            
            "Customer Journey SOPs (B2B & B2C)": {
                "Industry-Specific Journey": f"Customer journey optimization for {company_name} across B2B and B2C segments.",
                "Website & Funnel Analysis": f"Digital experience audit for {company_name} with conversion optimization recommendations."
            },
            
            "Competitive Advantage & Sector Inefficiencies": {
                "Competitive Edge": f"{company_name} competitive advantages and strategic market positioning analysis.",
                "Sector Pain Points & Operational Gaps": f"Industry opportunities representing growth potential for {company_name}."
            },
            
            "Workflow Automations & Growth Hacks": {
                "Most Pressing Pain Points": "Operational challenges requiring automation and process optimization.",
                "Quick Wins & Optimizations": "Immediate opportunities for rapid growth with minimal investment required.",
                "Alignment with Company Stage": f"Growth strategies tailored to {company_name} current market position."
            },
            
            "Conclusion & Next Steps": {
                "Key Findings": f"Critical insights for {company_name} strategic growth and market expansion.",
                "Actionable Priorities": f"Priority actions for {company_name} next quarter execution.",
                "Longer-Term Outlook": f"Strategic vision for {company_name} 12-24 month growth."
            },
            
            "Competitive Review and Comparison": {
                "Top Competitor Comparison Table": [
                    {
                        "Competitor": "Market Leader Alpha",
                        "Core Offering": "Comprehensive platform integrated technology",
                        "Technology Focus": "Advanced analytics mobile architecture",
                        "Target Market": "Enterprise clients multiple verticals",
                        "Competitive Advantage": "Market dominance comprehensive solutions",
                        "Strengths": "Established leadership strong technology",
                        "Weaknesses": "Higher costs limited innovation"
                    },
                    {
                        "Competitor": "Innovation Beta",
                        "Core Offering": "AI-powered solutions optimization focus",
                        "Technology Focus": "Machine learning predictive analytics",
                        "Target Market": "Tech-savvy forward-thinking organizations",
                        "Competitive Advantage": "Technology leadership innovation capability",
                        "Strengths": "Advanced technology sustainability focus",
                        "Weaknesses": "Limited presence higher complexity"
                    },
                    {
                        "Competitor": "Value Gamma",
                        "Core Offering": "Cost-efficient competitive pricing model",
                        "Technology Focus": "Reliable operational efficiency platform",
                        "Target Market": "Price-sensitive consumers SME businesses",
                        "Competitive Advantage": "Cost leadership operational efficiency",
                        "Strengths": "Price competitiveness market accessibility",
                        "Weaknesses": "Limited features basic technology"
                    }
                ]
            },
            
            "References and Citations": [
                f"Company website analysis for {website_url}",
                "Industry benchmarking competitive intelligence research",
                "Market trend analysis growth opportunities",
                "Strategic frameworks best practices review"
            ]
        }
    
    def save_json_report(self, report_data: dict, company_name: str) -> str:
        sanitized_name = re.sub(r'[^\w\-_\.]', '_', company_name.lower())
        json_filename = f"outputs/growth_report_concise_{sanitized_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            return json_filename
            
        except Exception as e:
            return None
    
    def create_pdf_report(self, report_data: dict, company_name: str, website_url: str) -> str:
        pdf = DynamicGrowthReportPDF(company_name)
        pdf.alias_nb_pages()
        pdf.add_page()
        
        pdf.set_font("Arial", style='B', size=16)
        pdf.set_text_color(0, 0, 0)
        
        title_text = f'“{company_name}” Growth Strategy & Operations Report'
        clean_title = pdf._clean_text_for_pdf(title_text)
        pdf.multi_cell(0, 8, clean_title, align='C')
        pdf.ln(12)
        
        section_handlers = {
            "Introduction": self._handle_introduction,
            "Company Offerings & Value Propositions": self._handle_company_offerings,
            "Customer Journey SOPs (B2B & B2C)": self._handle_customer_journey,
            "Competitive Advantage & Sector Inefficiencies": self._handle_competitive_advantage,
            "Workflow Automations & Growth Hacks": self._handle_workflow_automations,
            "Conclusion & Next Steps": self._handle_conclusion,
            "Competitive Review and Comparison": self._handle_competitive_review_concise,
        }
        
        section_counter = 1
        
        for section_title, content in report_data.items():
            if section_title == "References and Citations":
                continue
            
            pdf.check_page_break()
            pdf.add_section_header(section_counter, section_title)
            
            handler = section_handlers.get(section_title, self._handle_generic_section)
            handler(pdf, content)
            
            section_counter += 1
        
        if "References and Citations" in report_data:
            self._handle_references(pdf, report_data["References and Citations"], section_counter)
        
        sanitized_name = re.sub(r'[^\w\-_\.]', '_', company_name.lower())
        pdf_filename = f"outputs/“{sanitized_name}” Growth Strategy & Operations Optimization Report.pdf"
        
        
        pdf.output(pdf_filename)
        print(f"🎯 PDF report generated: {pdf_filename}")
        return pdf_filename
    
    def _handle_introduction(self, pdf: DynamicGrowthReportPDF, content):
        pdf.set_font("Arial", size=11)
        clean_content = pdf._clean_text_for_pdf(str(content))
        pdf.multi_cell(0, 6, clean_content)
        pdf.ln(5)
    
    def _handle_company_offerings(self, pdf: DynamicGrowthReportPDF, content):
        if isinstance(content, dict):
            for key, value in content.items():
                pdf.add_subsection(key, value)
    
    def _handle_customer_journey(self, pdf: DynamicGrowthReportPDF, content):
        if isinstance(content, dict):
            for key, value in content.items():
                pdf.add_subsection(key, value)
    
    def _handle_competitive_advantage(self, pdf: DynamicGrowthReportPDF, content):
        if isinstance(content, dict):
            for key, value in content.items():
                pdf.add_subsection(key, value)
    
    def _handle_workflow_automations(self, pdf: DynamicGrowthReportPDF, content):
        if isinstance(content, dict):
            for key, value in content.items():
                pdf.add_subsection(key, value)
    
    def _handle_conclusion(self, pdf: DynamicGrowthReportPDF, content):
        if isinstance(content, dict):
            for key, value in content.items():
                pdf.add_subsection(key, value)
    
    def _handle_competitive_review_concise(self, pdf: DynamicGrowthReportPDF, content):
        if isinstance(content, dict):
            for key, value in content.items():
                if key == "Top Competitor Comparison Table" and isinstance(value, list):
                    pdf._create_ultra_concise_table(value)
                else:
                    pdf.add_subsection(key, value)
    
    def _handle_references(self, pdf: DynamicGrowthReportPDF, content, section_num: int):
        if content and isinstance(content, list):
            pdf.check_page_break()
            pdf.add_section_header(section_num, "References and Citations")
            
            pdf.set_font("Arial", size=10)
            for i, ref in enumerate(content, 1):
                if pdf.get_y() > 275:
                    pdf.add_page()
                clean_ref = pdf._clean_text_for_pdf(ref)
                pdf.multi_cell(0, 5, f"{i}. {clean_ref}")
                pdf.ln(2)
    
    def _handle_generic_section(self, pdf: DynamicGrowthReportPDF, content):
        if isinstance(content, dict):
            for key, value in content.items():
                pdf.add_subsection(key, value)
        elif isinstance(content, list):
            for item in content:
                clean_item = pdf._clean_text_for_pdf(str(item))
                pdf.add_bullet_point(clean_item)
        else:
            pdf.set_font("Arial", size=11)
            clean_content = pdf._clean_text_for_pdf(str(content))
            pdf.multi_cell(0, 6, clean_content)


def growth_optimization_node(state: GraphState) -> dict:
    try:
        generator = GrowthReportGenerator()
        
        website_url = None
        if hasattr(state, 'website_url') and state.website_url:
            website_url = state.website_url
        else:
            website_url = generator.load_website_url()
        
        prompt_template = generator.load_prompt_template()
        company_name = generator.extract_company_name(website_url)
        report_data = generator.generate_report_content(website_url, prompt_template)
        
        if not isinstance(report_data, dict) or not report_data:
            report_data = generator._create_enhanced_fallback_report(website_url)
        
        json_path = generator.save_json_report(report_data, company_name)
        pdf_path = generator.create_pdf_report(report_data, company_name, website_url)
        
        state_update = {
            "GR_JSON": report_data,
            "growth_report_data": report_data,
            "growth_analysis_complete": True,
            "company_name": company_name,
            "website_url": website_url,
            "json_path": json_path,
            "pdf_path": pdf_path,
            "timestamp": datetime.now().isoformat()
        }
        
        if hasattr(state, 'model_dump'):
            return {**state.model_dump(), **state_update}
        elif hasattr(state, 'dict'):
            return {**state.dict(), **state_update}
        else:
            return {**dict(state), **state_update}
        
    except Exception as e:
        fallback_report = {
            "Introduction": f"Analysis failed for {website_url if 'website_url' in locals() else 'unknown website'}",
            "error": str(e),
            "status": "failed_with_fallback"
        }
        
        fallback_update = {
            "GR_JSON": fallback_report,
            "growth_report_data": fallback_report,
            "growth_analysis_complete": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if hasattr(state, 'model_dump'):
                return {**state.model_dump(), **fallback_update}
            elif hasattr(state, 'dict'):
                return {**state.dict(), **fallback_update}
            else:
                return {**dict(state), **fallback_update}
        except:
            return {
                "website_url": website_url if 'website_url' in locals() else "",
                **fallback_update
            }


if __name__ == "__main__":
    class DummyState:
        def __init__(self):
            self.website_url = None
        
        def dict(self):
            return {"website_url": self.website_url}
        
        def model_dump(self):
            return {"website_url": self.website_url}
    
    try:
        result = growth_optimization_node(DummyState())
    except Exception as e:
        pass