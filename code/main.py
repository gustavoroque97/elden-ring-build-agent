import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph
from IPython.display import Markdown

from vectorstore import setup_retrievers
from nodes import BuildNodes
from graph import create_build_graph

def generate_elden_ring_build(user_request: str, app: CompiledStateGraph) -> None:
    """
    Execute the workflow for the provided user request.
    
    Parameters
    ----------
    user_request : str
        The query specifying the desired Elden Ring build.
    app : CompiledStateGraph
        The compiled workflow graph to invoke.
        
    Returns
    -------
    None
    """
    print(f"\\n{'='*50}\\nInitiating Build: '{user_request}'\\n{'='*50}")
    
    initial_state = {
        "query": user_request,
        "is_valid": True,
        "rejection_reason": "",
        "starting_class": "",
        "use_incantations": False,
        "use_sorceries": False,
        "use_shields": False,
        "use_ammos": False,
        "weapons": [], "armor": [], "talismans": [], "spirits": [],
        "incantations": [], "sorceries": [], "shields": [], "ammos": [],
        "final_build": ""
    }
    
    result = app.invoke(initial_state)
    
    if not result.get("is_valid"):
        print("\\nBuild Request Denied:")
 
    else:
        print("\\nBuild Generation Complete!\\n")
        
    return Markdown(result["final_build"])

def main() -> None:
    """
    Main entry point for initializing components and executing an example generation.
    """
    load_dotenv()
    
    print("Setting up vector store retrievers...")
    retrievers = setup_retrievers(data_dir="data/rag_data", index_path="data/faiss_index")
    
    print("Initializing language model...")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    nodes_instance = BuildNodes(llm=llm, retrievers=retrievers)
    
    app = create_build_graph(nodes_instance=nodes_instance)
    
    # Example execution
    user_query = "I want a dragon communion build"
    generate_elden_ring_build(user_query, app)

if __name__ == "__main__":
    main()
