from typing import Dict, List, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores import VectorStoreRetriever

from models import BuildState, QueryValidation, OptionalsDecision, CategoryExtraction

class BuildNodes:
    """
    Contains the LangGraph node functions for processing Elden Ring build requests.
    """

    def __init__(self, llm: BaseChatModel, retrievers: Dict[str, VectorStoreRetriever]):
        """
        Initialize the BuildNodes with a language model and retrievers.
        
        Parameters
        ----------
        llm : BaseChatModel
            The chat model to use for LLM invocations.
        retrievers : Dict[str, VectorStoreRetriever]
            The dictionary of vector store retrievers categorized by gear type.
        """
        self.llm = llm
        self.retrievers = retrievers

    def validate_query_node(self, state: BuildState) -> Dict[str, Any]:
        """
        Validate if the query is a feasible Elden Ring build.
        
        Parameters
        ----------
        state : BuildState
            The current state of the graph.
            
        Returns
        -------
        Dict[str, Any]
            Updates to the state including validity, reason, and final build (if rejected).
        """
        print("--- 0. Validating Query (Gatekeeper) ---")
        query = state["query"]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", '''You are the Gatekeeper of the Lands Between. 
            Your job is to evaluate user requests for Elden Ring character builds.
            
            CRITICAL RULES:
            1. Reject requests for modern technology (guns, AK-47s, cars, lasers).
            2. Reject requests for items from other video games (e.g., Master Sword from Zelda, lightsabers).
            3. Reject completely unrelated topics (cooking recipes, coding help).
            4. Accept ANY feasible Elden Ring concept (magic, swords, incantations, cosplay builds, status effects).
            
            Evaluate the query and determine if it is a valid Elden Ring build request.'''),
            ("user", "Query: {query}")
        ])
        
        chain = prompt | self.llm.with_structured_output(QueryValidation)
        decision = chain.invoke({"query": query})
        
        if not decision.is_valid:
            print(f"     [REJECTED]: {decision.rejection_reason}")
            
        return {
            "is_valid": decision.is_valid,
            "rejection_reason": decision.rejection_reason,
            "final_build": decision.rejection_reason if not decision.is_valid else "" 
        }

    def select_class_node(self, state: BuildState) -> Dict[str, Any]:
        """
        Select the best starting class based on the query.
        
        Parameters
        ----------
        state : BuildState
            The current state containing the query.
            
        Returns
        -------
        Dict[str, Any]
            State update with the selected starting class.
        """
        print("--- 1. Selecting Class ---")
        query = state["query"]
        
        retrieved_docs = self.retrievers['classes'].invoke(f"Starting classes stats for {query}")
        context = "\\n\\n".join([d.page_content for d in retrieved_docs])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", '''You are a strict Elden Ring data extractor. 
            Select the SINGLE best starting class for the user's build.
            
            CRITICAL RULES:
            1. You MUST select the class ONLY from the text provided in the Context below.
            2. DO NOT invent classes or use outside knowledge.
            3. If you do not find a better fit class, choose 'Wretch'.
            4. If a specific class is passed, choose this class if it exists on the Context below. If not, choose by the Context.
            5. Return only the selected class, without any further explanation.
            
            Context:
            {context}'''),
            ("user", "Query: {query}")
        ])
        
        selected_class = (prompt | self.llm).invoke({"context": context, "query": query}).content.strip()
        return {"starting_class": selected_class}

    def decide_optionals_node(self, state: BuildState) -> Dict[str, Any]:
        """
        Determine which optional gear categories are relevant for the build.
        
        Parameters
        ----------
        state : BuildState
            The current state containing query and starting class.
            
        Returns
        -------
        Dict[str, Any]
            State update indicating the requirement of incantations, sorceries, shields, and ammo.
        """
        print("--- 2. Deciding Optionals ---")
        prompt = ChatPromptTemplate.from_messages([
             ("system", "You are an Elden Ring expert. The user wants to build a '{query}'. They are starting as a {starting_class}. Decide if this build typically requires or benefits from Incantations, Sorceries, Shields, and Ammos."),
        ])
        chain = prompt | self.llm.with_structured_output(OptionalsDecision)
        decision = chain.invoke({"query": state["query"], "starting_class": state.get("starting_class", "Wretch")})
        
        return {
            "use_incantations": decision.use_incantations,
            "use_sorceries": decision.use_sorceries,
            "use_shields": decision.use_shields,
            "use_ammos": decision.use_ammos
        }

    def extract_gear_category(self, build_query: str, starting_class: str, category_name: str, instructions: str) -> List[str]:
        """
        Retrieve and extract items for a specific gear category.
        
        Parameters
        ----------
        build_query : str
            The user's requested build theme.
        starting_class : str
            The starting class choosen for the build.
        category_name : str
            The name of the gear category to extract.
        instructions : str
            Specific target quantity and slot rules for the prompt.
            
        Returns
        -------
        List[str]
            A list of extracted item names for the category.
        """
        print(f"  -> Retrieving {category_name}...")
        
        specific_retriever = self.retrievers.get(category_name)
        if not specific_retriever:
            print(f"     [Error] No retriever found for {category_name}.")
            return []

        docs = specific_retriever.invoke(f"best {category_name} for {build_query} build")
        
        if not docs:
            print(f"     [Fallback] Fetching general {category_name}...")
            docs = specific_retriever.invoke(f"good {category_name} for the {starting_class} class")

        context = "\\n\\n".join([d.page_content for d in docs])
        
        prompt = ChatPromptTemplate.from_messages([
             ("system", '''You are a strict Elden Ring data extractor. 
             Extract the best {category_name} for a '{build_query}' build starting as '{starting_class}'.
             
             TARGET QUANTITY & SLOTS:
             {instructions}
             
             CRITICAL RULES:
             1. You MUST ONLY extract {category_name} explicitly named in the Context below.
             2. Try your absolute best to fulfill the TARGET QUANTITY using the context.
             3. DO NOT rely on your general knowledge.
             
             Context:
             {context}'''),
             ("user", "Extract the {category_name} using ONLY the context.")
        ])
        
        chain = prompt | self.llm.with_structured_output(CategoryExtraction)
        decision = chain.invoke({
            "build_query": build_query, 
            "starting_class": starting_class, 
            "category_name": category_name,
            "instructions": instructions,
            "context": context
        })
        
        return decision.items

    def select_core_gear_node(self, state: BuildState) -> Dict[str, Any]:
        """
        Select core gear (weapons, armor, talismans, spirits) for the build.
        
        Parameters
        ----------
        state : BuildState
            The current state.
            
        Returns
        -------
        Dict[str, Any]
            State update with core gear selections.
        """
        print("--- 3. Selecting Core Gear (Parallel Extraction) ---")
        query = state["query"]
        starting_class = state.get("starting_class", "Wretch")
        
        weapons = self.extract_gear_category(
            query, starting_class, "weapons", 
            "Extract exactly 2 weapons. Ideally a primary weapon and a secondary/off-hand weapon."
        )
        
        armor = self.extract_gear_category(
            query, starting_class, "armor", 
            '''Extract exactly 1 piece of armor that better fit the build. By the armor extracted,
            define the armor set that will be used.'''
        )
        
        talismans = self.extract_gear_category(
            query, starting_class, "talismans", 
            "Extract exactly 4 distinct talismans to fill all available talisman pouches."
        )
        
        spirits = self.extract_gear_category(
            query, starting_class, "spirit ashes", 
            "Extract exactly 2 distinct Spirit Ashes that fit this build."
        )
        
        return {
            "weapons": weapons,
            "armor": armor,
            "talismans": talismans,
            "spirits": spirits
        }

    def select_optional_gear_node(self, state: BuildState) -> Dict[str, Any]:
        """
        Select optional gear based on previous decisions.
        
        Parameters
        ----------
        state : BuildState
            The current state.
            
        Returns
        -------
        Dict[str, Any]
            State update with optional gear selections.
        """
        print("--- 4. Selecting Optional Gear (Parallel Extraction) ---")
        query = state["query"]
        starting_class = state.get("starting_class", "Wretch")
        
        ret_data = {}
        
        if state.get("use_incantations"):
            ret_data["incantations"] = self.extract_gear_category(
                query, starting_class, "incantations", 
                "Extract 4 highly effective incantations that fit this build's theme and stats."
            )
            
        if state.get("use_sorceries"):
            ret_data["sorceries"] = self.extract_gear_category(
                query, starting_class, "sorceries", 
                "Extract 4 highly effective sorceries that fit this build's theme and stats."
            )
            
        if state.get("use_shields"):
            ret_data["shields"] = self.extract_gear_category(
                query, starting_class, "shields", 
                "Extract 1 highly effective shield suitable for this build's weight and playstyle."
            )
            
        if state.get("use_ammos"):
            ret_data["ammos"] = self.extract_gear_category(
                query, starting_class, "ammos", 
                "Extract 2 specific types of arrows or bolts that synergize with this build."
            )
            
        return ret_data

    def compile_build_node(self, state: BuildState) -> Dict[str, Any]:
        """
        Compile all selections into a final markdown guide.
        
        Parameters
        ----------
        state : BuildState
            The state with all gear selections.
            
        Returns
        -------
        Dict[str, Any]
            State update with the generated final_build markdown text.
        """
        print("--- 5. Compiling Final Build ---")
        
        prompt = ChatPromptTemplate.from_messages([
                    ("system", """You are a master Elden Ring build guide author. Output a highly detailed, beautifully formatted markdown guide for the requested build. 
                    
                    CRITICAL RULES FOR SYNTHESIS:
                    1. FORMATTING: You MUST use proper markdown spacing. Leave a blank line before and after every header (## or ###) and every list.
                    2. THE ARMOR RULE: Look at the provided 'Armor' list. Use your knowledge to identify the full Armor Set that those pieces belong to, and recommend wearing that complete set. (e.g., If given 'Crucible Axe Helm', recommend the full 'Crucible Axe Set').
                    3. DO NOT FILL SLOTS: You are STRICTLY FORBIDDEN from adding, inventing, or recommending any weapons, talismans, spirits, or spells that are not explicitly provided in the prompt. 
                    4. ACCEPT INCOMPLETE LISTS: If you are only provided 2 talismans, ONLY discuss those 2. Do not suggest a 3rd or 4rd talisman. If a category is completely empty, skip mentioning it entirely.
                    
                    Explain the synergy of the items provided, how to play the build, and how the stats should align."""),
                    
                    ("user", """Build Query: {query}
        Class: {starting_class}
        Weapons: {weapons}
        Armor: {armor}
        Talismans: {talismans}
        Spirits: {spirits}
        Incantations: {incantations}
        Sorceries: {sorceries}
        Shields: {shields}
        Ammos: {ammos}

        Write the guide!""")
                ])
        
        final_text = (prompt | self.llm).invoke({
            "query": state["query"],
            "starting_class": state.get("starting_class", "Any"),
            "weapons": ", ".join(state.get("weapons", [])),
            "armor": ", ".join(state.get("armor", [])),
            "talismans": ", ".join(state.get("talismans", [])),
            "spirits": ", ".join(state.get("spirits", [])),
            "incantations": ", ".join(state.get("incantations", [])),
            "sorceries": ", ".join(state.get("sorceries", [])),
            "shields": ", ".join(state.get("shields", [])),
            "ammos": ", ".join(state.get("ammos", []))
        }).content
        
        return {"final_build": final_text}
