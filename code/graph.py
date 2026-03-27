from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from models import BuildState
from nodes import BuildNodes

def route_after_validation(state: BuildState) -> str:
    """
    Route the workflow after validating the user query.
    
    Parameters
    ----------
    state : BuildState
        The current state.
        
    Returns
    -------
    str
        The name of the next node to execute.
    """
    if state.get("is_valid"):
        print("  -> Gatekeeper Approved: Proceeding to Class Selection.")
        return "select_class_node"
    else:
        print("  -> Gatekeeper Rejected: Aborting workflow.")
        return END

def route_optional_gear(state: BuildState) -> str:
    """
    Determine whether to route to optional gear selection.
    
    Parameters
    ----------
    state : BuildState
        The current state.
        
    Returns
    -------
    str
        The name of the next node to execute.
    """
    needs_optionals = (
        state.get("use_incantations") or 
        state.get("use_sorceries") or 
        state.get("use_shields") or 
        state.get("use_ammos")
    )
    
    if needs_optionals:
        print("  -> Optionals required. Routing to Optional Gear Extraction.")
        return "select_optional_gear"
    else:
        print("  -> No optionals needed. Bypassing straight to Compilation.")
        return "compile_build"

def create_build_graph(nodes_instance: BuildNodes) -> CompiledStateGraph:
    """
    Construct and compile the LangGraph workflow.
    
    Parameters
    ----------
    nodes_instance : BuildNodes
        An instance of BuildNodes containing the initialized node functions.
        
    Returns
    -------
    CompiledStateGraph
        The runnable LangGraph application.
    """
    workflow = StateGraph(BuildState)

    workflow.add_node("validate_query", nodes_instance.validate_query_node)
    workflow.add_node("select_class_node", nodes_instance.select_class_node)
    workflow.add_node("decide_optionals", nodes_instance.decide_optionals_node)
    workflow.add_node("select_core_gear", nodes_instance.select_core_gear_node)
    workflow.add_node("select_optional_gear", nodes_instance.select_optional_gear_node)
    workflow.add_node("compile_build", nodes_instance.compile_build_node)

    workflow.add_edge(START, "validate_query")

    workflow.add_conditional_edges(
        "validate_query", 
        route_after_validation, 
        {
            "select_class_node": "select_class_node",
            END: END 
        }
    )

    workflow.add_edge("select_class_node", "decide_optionals")
    workflow.add_edge("decide_optionals", "select_core_gear")
    workflow.add_conditional_edges(
        "select_core_gear",    
        route_optional_gear,   
        {
            "select_optional_gear": "select_optional_gear", 
            "compile_build": "compile_build"                
        }
    )
    workflow.add_edge("select_optional_gear", "compile_build")
    workflow.add_edge("compile_build", END)

    app = workflow.compile()
    print("Graph compiled successfully! Ready for queries.")
    
    return app
