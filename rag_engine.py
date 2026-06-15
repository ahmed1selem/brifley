import os
import json
import wikipedia
from openai import OpenAI
from vdb_helper import VectorDBHelper
from clustering import get_embedder

class RAGEngine:
    def __init__(self):
        # Set up Local Ollama client using the OpenAI SDK
        self.client = OpenAI(
            api_key="ollama", # Required by the SDK, but unused by Ollama
            base_url="http://localhost:11434/v1",
        )
        # Using local llama3.2 which supports tool calling natively!
        self.model = "llama3.2:latest"
        
        self.vdb = VectorDBHelper()
        self.embedder = get_embedder()

    # ==========================================
    # SKILL 1: Cluster Fetcher
    # ==========================================
    def fetch_cluster_details(self, cluster_id: str, preferred_sources: list = None) -> str:
        """Fetch all articles strictly belonging to a single news cluster."""
        print(f"[Skill Execution] Fetching details for cluster '{cluster_id}'")
        articles = self.vdb.get_by_cluster(str(cluster_id), preferred_sources=preferred_sources)
        
        if not articles:
            return f"No articles found for cluster {cluster_id}."
            
        context = ""
        for i, art in enumerate(articles):
            p = art["payload"]
            title = p.get("title", "No Title")
            text = p.get("full_text", p.get("summary_text", "No Text"))
            context += f"\n--- Article {i+1} ---\nTitle: {title}\nContent: {text}\n"
        return context

    # ==========================================
    # SKILL 2: Global Vector Search
    # ==========================================
    def global_vector_search(self, query: str, preferred_sources: list = None) -> str:
        """Search the entire database for general breaking news queries."""
        print(f"[Skill Execution] Searching global vector DB for '{query}'")
        embedding = self.embedder.encode([query], show_progress_bar=False)[0].tolist()
        
        results = self.vdb.search_similar(embedding, top_k=5, preferred_sources=preferred_sources)
        
        if not results:
            return "No relevant articles found in the database."
            
        context = ""
        for i, hit in enumerate(results):
            p = hit["payload"]
            title = p.get("title", "No Title")
            text = p.get("full_text", p.get("summary_text", "No Text"))
            score = hit["score"]
            context += f"\n--- Article {i+1} (Relevance: {score:.2f}) ---\nTitle: {title}\nContent: {text}\n"
        return context

    # ==========================================
    # SKILL 3: Wikipedia Search
    # ==========================================
    def search_wikipedia(self, query: str) -> str:
        """Search Wikipedia for historical context and background info."""
        print(f"[Skill Execution] Searching Wikipedia for '{query}'")
        try:
            # Set sentences=3 to get a concise summary
            summary = wikipedia.summary(query, sentences=3)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            return f"Query is too broad. Did you mean one of these? {e.options[:5]}"
        except wikipedia.exceptions.PageError:
            return "No Wikipedia page found for this query."
        except Exception as e:
            return f"Error searching Wikipedia: {str(e)}"

    # ==========================================
    # THE AGENT ROUTER
    # ==========================================
    def ask(self, user_question: str, current_cluster_id: str = None, preferred_sources: list = None) -> str:
        """
        The main Agentic RAG entrypoint.
        Provides the LLM with the 3 skills and lets it decide what to use.
        """
        system_prompt = (
            "You are an expert journalistic AI assistant. You have access to three tools:\n"
            "1. 'fetch_cluster_details' for deep dives into a specific breaking news cluster.\n"
            "2. 'global_vector_search' for searching all recent news.\n"
            "3. 'search_wikipedia' for historical context and definitions.\n"
            "Choose the right tool to answer the user's question accurately. "
            "You MUST base your final answer on the context provided by these tools. "
            "If the context doesn't contain the answer, say 'I don't have enough information.' "
            "Always cite your sources."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question}
        ]
        
        # If the user is viewing a specific cluster, hint it to the LLM
        if current_cluster_id:
            messages.append({
                "role": "user", 
                "content": f"[SYSTEM HINT] The user is currently viewing cluster ID '{current_cluster_id}'. If they ask 'what is this about', use fetch_cluster_details."
            })

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "fetch_cluster_details",
                    "description": "Fetch articles belonging to a specific news cluster ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cluster_id": {
                                "type": "string",
                                "description": "The ID of the cluster to fetch."
                            }
                        },
                        "required": ["cluster_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "global_vector_search",
                    "description": "Search the entire news database for articles matching a general query.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query (e.g. 'Tech news 2024')."
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_wikipedia",
                    "description": "Search Wikipedia for historical background or definitions of terms.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The Wikipedia search query."
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        print("Thinking...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            return f"Error connecting to Together.ai: {e}"

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # If the LLM decided to use a tool
        if tool_calls:
            # Add the assistant's tool call message to the history
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the correct skill
                if function_name == "fetch_cluster_details":
                    tool_result = self.fetch_cluster_details(function_args.get("cluster_id"), preferred_sources)
                elif function_name == "global_vector_search":
                    tool_result = self.global_vector_search(function_args.get("query"), preferred_sources)
                elif function_name == "search_wikipedia":
                    tool_result = self.search_wikipedia(function_args.get("query"))
                else:
                    tool_result = "Error: Unknown function."

                # Append the tool's result to the context
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": tool_result
                })

            # Send the retrieved context back to the LLM to generate the final answer
            print("Generating final answer based on retrieved context...")
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            return final_response.choices[0].message.content

        # If the LLM didn't need a tool (rare for RAG)
        return response_message.content

if __name__ == "__main__":
    # Test the Local Agent via Ollama
    print("Initializing Local RAG Engine (Ollama Llama 3.2)...")
    engine = RAGEngine()
    print("\n--- TEST 1: Wikipedia Skill ---")
    print(engine.ask("What is the history of the United Nations?"))
    
    print("\n--- TEST 2: Global Search Skill ---")
    print(engine.ask("Are there any news about elections?"))
