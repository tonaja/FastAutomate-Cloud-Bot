import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from graph_state import GraphState


load_dotenv()


from nodes.node_a_growth_optimization import growth_optimization_node
from nodes.node_b_icp_generator import icp_generator_node
from nodes.node_c_search_query import search_query_generator_node


def create_workflow_graph():
    workflow = StateGraph(GraphState)
    
    workflow.add_node("A_GrowthOptimization", growth_optimization_node)
    workflow.add_node("B_ICPGenerator", icp_generator_node)
    workflow.add_node("C_SearchQueryGenerator", search_query_generator_node)
    
    workflow.set_entry_point("A_GrowthOptimization")
    workflow.add_edge("A_GrowthOptimization", "B_ICPGenerator")
    workflow.add_edge("B_ICPGenerator", "C_SearchQueryGenerator")
    workflow.add_edge("C_SearchQueryGenerator", END)
    
    return workflow.compile()


def run_graph_with_full_output(input_dict):
    try:
        print("Starting workflow execution...")
        graph = create_workflow_graph()
        result = graph.invoke(input_dict)
        
        state_data = result
        
        icp_data = state_data.get("ICP_GENERATOR_JSON", {})
        search_query_data = state_data.get("SEARCH_QUERY_JSON", {})
        
        summary = {
            "total_icps_generated": len(icp_data.get("b2bICPTable", {}).get("icpProfiles", [])),
            "total_personas_generated": len(icp_data.get("buyerPersonasTable", {}).get("personas", [])),
            "total_search_queries": search_query_data.get("total_queries", 0),
            "pdf_report_path": icp_data.get("pdf_report_path", ""),
            "search_queries_path": search_query_data.get("queries_file_path", ""),
            "company_name": icp_data.get("company_name", ""),
            "model_used": icp_data.get("model_used", "")
        }
        
        return {
            **state_data,
            "workflow_summary": summary
        }
        
    except Exception as e:
        print(f"Workflow error: {e}")
        raise


def main_PrimeLeads(website_url_file):
    try:
        website_url_file
        if os.path.exists(website_url_file):
            website_url = open(website_url_file, encoding="utf-8").read().strip()
        else:
            raise FileNotFoundError(f"Website URL file not found: {website_url_file}")

        print(f"Processing URL: {website_url}")
        result = run_graph_with_full_output({"website_url": website_url})
        summary = result.get("workflow_summary", {})

        print("\nWorkflow results:")
        print(f"Company: {summary.get('company_name')}")
        print(f"ICPs Generated: {summary.get('total_icps_generated')}")
        print(f"Personas Created: {summary.get('total_personas_generated')}")
        print(f"Search Queries: {summary.get('total_search_queries')}")
        
        pdf_path = summary.get('pdf_report_path')
        if pdf_path and os.path.exists(pdf_path):
            print(f"PDF Report generated: {pdf_path}")
        
        queries_path = summary.get('search_queries_path')
        if queries_path and os.path.exists(queries_path):
            print(f"Search queries file generated: {queries_path}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Workflow failed: {e}")