"""Nodes for the agentic RAG workflow."""



import ast
import logging
from concurrent.futures import ThreadPoolExecutor

from app.agent.llm.base import LLMProvider
from app.agent.state import AgentState, CodeArtifact
from app.retrieval.retriever import SemanticRetriever
from app.services.coding_service import CodingService
from app.services.web_search_service import WebSearchService

logger = logging.getLogger(__name__)





class AgentNodes:

    """Implement the individual nodes used by the agentic RAG workflow."""



    def __init__(

        self,

        retriever: SemanticRetriever,

        llm_provider: LLMProvider,

        *,

        openai_provider: LLMProvider | None = None,

        gemini_provider: LLMProvider | None = None,

        web_search_service: WebSearchService | None = None,

        coding_service: CodingService | None = None,

        max_retrieval_attempts: int = 2,

    ) -> None:

        """Initialize agent nodes."""



        if max_retrieval_attempts <= 0:



            raise ValueError("max_retrieval_attempts must be greater than zero")



        self._retriever = retriever



        self._llm_provider = llm_provider



        self._openai_provider = openai_provider



        self._gemini_provider = gemini_provider



        self._web_search_service = web_search_service or WebSearchService()



        self._coding_service = coding_service



        self._max_retrieval_attempts = max_retrieval_attempts



    # ------------------------------------------------------------------



    # PLANNER



    # ------------------------------------------------------------------



    def planner(self, state: AgentState) -> AgentState:

        """Classify the user's request and select the appropriate route."""



        query = state.query.strip()



        user_id = state.user_id.strip()



        if not query:



            raise ValueError("query cannot be empty")



        if not user_id:



            raise ValueError("user_id cannot be empty")



        state.query = query



        state.user_id = user_id



        query_lower = query.lower()



        # Explicit document/file requests should use RAG.



        rag_terms = (

            "uploaded",

            "document",

            "file",

            "pdf",

            "docx",

            "txt",

            "csv",

            "xlsx",

            "spreadsheet",

            "pptx",

            "slide",

            "according to the document",

            "in the document",

            "from the document",

        )



        # Calculator requests.



        calculator_terms = (

            "calculate",

            "calculator",

        )



        # Weather requests.



        weather_terms = (

            "weather",

            "temperature",

            "forecast",

            "rain today",

            "will it rain",

        )



        # Web/current-information requests.



        web_terms = (

            "latest",

            "today",

            "current",

            "news",

            "recent",

            "search the web",

            "look online",

        )



        no_web_terms = (

            "do not search the web",

            "don't search the web",

            "do not use the web",

            "don't use the web",

            "without searching the web",

            "without web search",

            "no web search",

        )



        # Coding requests must be checked before RAG because requests such as

        # "convert this Python file to Java" also contain the word "file".

        if self._looks_like_coding_request(query_lower, state):

            state.route = "coding"

        elif any(term in query_lower for term in rag_terms):

            state.route = "rag"

        elif any(term in query_lower for term in weather_terms):

            state.route = "weather"

        elif any(term in query_lower for term in calculator_terms):

            state.route = "calculator"

        elif (

            any(term in query_lower for term in web_terms)

            and not any(term in query_lower for term in no_web_terms)

        ):

            state.route = "web"

        elif self._looks_like_calculation(query):

            state.route = "calculator"

        else:

            state.route = "general"



        return state



    # ------------------------------------------------------------------



    # RETRIEVER



    # ------------------------------------------------------------------



    def retrieve(self, state: AgentState) -> AgentState:

        """Retrieve relevant chunks for document-based requests."""



        # General questions and tool requests do not need document



        # retrieval.



        if state.route != "rag":



            state.retrieved_chunks = []



            return state



        if state.retrieval_attempts >= self._max_retrieval_attempts:



            state.error = "Maximum retrieval attempts reached."



            return state



        results = self._retriever.retrieve(

            query=state.query,

            user_id=state.user_id,

            document_id=state.document_id,

            top_k=5,

        )



        state.retrieved_chunks = [

            {

                "chunk_id": result.chunk_id,

                "text": result.text,

                "metadata": result.metadata,

            }

            for result in results

        ]



        state.retrieval_attempts += 1



        return state



    # ------------------------------------------------------------------



    # GENERATOR



    # ------------------------------------------------------------------



    def generate(self, state: AgentState) -> AgentState:

        """Generate an answer using the selected route."""



        # --------------------------------------------------------------

        # CODING ASSISTANT

        # --------------------------------------------------------------



        if state.route == "coding":

            return self._generate_coding_answer(state)



        # --------------------------------------------------------------



        # GENERAL AI ASSISTANT



        # --------------------------------------------------------------



        if state.route == "general":



            return self._generate_general_answer(state)



        # --------------------------------------------------------------



        # CALCULATOR



        # --------------------------------------------------------------



        if state.route == "calculator":



            return self._generate_calculator_answer(state)



        # --------------------------------------------------------------



        # WEATHER



        # --------------------------------------------------------------



        if state.route == "weather":



            state.answer = (

                "Weather tools are not connected yet. "

                "The weather tool will be added in the next implementation "

                "step."

            )



            return state



        # --------------------------------------------------------------



        # WEB SEARCH



        # --------------------------------------------------------------



        if state.route == "web":



            return self._generate_web_answer(state)



        # --------------------------------------------------------------



        # DOCUMENT RAG



        # --------------------------------------------------------------



        if state.route == "rag":



            return self._generate_rag_answer(state)



        state.answer = "I could not determine how to handle this request."



        return state



    # ------------------------------------------------------------------



    # GENERAL ANSWER



    # ------------------------------------------------------------------



    @staticmethod

    def _looks_like_coding_request(query_lower: str, state: AgentState) -> bool:

        """Determine whether the request should use the coding workflow."""

        coding_terms = (

            "convert",

            "conversion",

            "translate this code",

            "rewrite this code",

            "rewrite",

            "refactor",

            "debug",

            "fix this code",

            "fix the code",

            "modify this code",

            "change this code",

            "improve this code",

            "optimize this code",

            "explain this code",

            "code",

            "program",

            "function",

            "class",

            "python",

            "java",

            "javascript",

            "typescript",

            "c++",

            "c#",

            "golang",

            "rust",

        )

        if state.code_artifact is not None:

            return any(term in query_lower for term in coding_terms)

        return any(

            term in query_lower

            for term in (

                "convert",

                "rewrite this code",

                "translate this code",

                "refactor",

                "debug",

                "fix this code",

                "fix the code",

                "modify this code",

                "change this code",

            )

        )



    def _generate_coding_answer(self, state: AgentState) -> AgentState:

        """Generate or modify code using the current conversation artifact."""

        if self._coding_service is None:

            state.answer = "The coding service is not configured."

            state.error = "CodingService dependency is missing."

            return state

        if state.code_artifact is None:

            state.answer = (

                "I need source code before I can modify or convert it. "

                "Please upload or provide the code first."

            )

            state.error = "No code artifact is available."

            return state

        try:

            result = self._coding_service.generate_solution(

                source_code=state.code_artifact.source_code,

                user_instruction=state.query,

                source_filename=state.code_artifact.filename,

            )

        except Exception as exc:

            state.answer = "I could not generate the requested code. Please try again."

            state.error = str(exc)

            return state

        solution_code = str(result.get("solution_code", "")).strip()

        explanation = str(result.get("explanation", "")).strip()

        language = str(result.get("language", "")).strip().lower()

        extension = str(result.get("extension", "")).strip()

        if not solution_code:

            state.answer = "The coding service did not return any generated code."

            state.error = "Empty coding service result."

            return state

        source_filename = state.code_artifact.filename

        base_name = source_filename.rsplit(".", 1)[0]

        generated_filename = f"{base_name}_solution{extension}"

        state.generated_code_artifact = CodeArtifact(

            filename=generated_filename,

            language=language,

            source_code=solution_code,

        )

        state.answer = (

            f"Generated {language or 'target'} code successfully.\n\n"

            f"### Generated Code\n\n"

            f"```{language or 'text'}\n{solution_code}\n```\n\n"

            f"### Explanation\n\n"

            f"{explanation or 'No additional explanation was provided.'}"

        )

        state.verification_passed = True

        state.verification_reason = (

            "The coding request was processed using the coding workflow."

        )

        return state



    def _generate_web_answer(self, state: AgentState) -> AgentState:

        """Search the web and generate an answer from the results."""



        try:



            results = self._web_search_service.search(

                state.query,

                max_results=5,

            )



        except Exception as exc:

            logger.exception("Web search failed for query: %s", state.query)

            state.answer = (

                "I could not search the web right now. " "Please try again shortly."

            )



            state.error = str(exc)



            return state



        if not results:



            state.answer = "I could not find relevant web results for your question."



            return state



        result_lines = []



        for index, result in enumerate(results, start=1):



            result_lines.append(

                f"[Source {index}]\n"

                f"Title: {result['title']}\n"

                f"URL: {result['url']}\n"

                f"Snippet: {result['snippet']}"

            )



        state.tool_result = "\n\n".join(result_lines)



        history = self._format_conversation_history(state)



        system_prompt = (

            "You are a helpful web-enabled AI assistant. "

            "Answer the user's question using the web search results provided. "

            "Prefer information supported by the search results. "

            "Do not invent facts that are not supported by the results. "

            "When the results are insufficient, clearly say so. "

            "Include the relevant source URLs in your answer."

        )



        user_prompt = (

            f"Conversation history:\n{history}\n\n"

            f"User question:\n{state.query}\n\n"

            f"Web search results:\n{state.tool_result}"

        )



        return self._generate_with_available_providers(

            state=state,

            system_prompt=system_prompt,

            user_prompt=user_prompt,

        )



    def _generate_general_answer(self, state: AgentState) -> AgentState:

        """Generate a general-purpose answer without document retrieval."""



        history = self._format_conversation_history(state)



        system_prompt = (

            "You are a helpful general-purpose AI assistant. "

            "Answer the user's question clearly, accurately, and naturally. "

            "Use the conversation history when it is relevant. "

            "Do not invent information from documents that were not provided."

        )



        user_prompt = (

            f"Conversation history:\n{history}\n\n" f"User question:\n{state.query}"

        )



        return self._generate_with_available_providers(

            state=state,

            system_prompt=system_prompt,

            user_prompt=user_prompt,

        )



    # ------------------------------------------------------------------



    # RAG ANSWER



    # ------------------------------------------------------------------



    def _generate_rag_answer(self, state: AgentState) -> AgentState:

        """Generate an answer grounded in retrieved document evidence."""



        if not state.retrieved_chunks:



            state.answer = (

                "I could not find relevant information in your documents "

                "to answer this question."

            )



            return state



        context = self._build_document_context(state)



        history = self._format_conversation_history(state)



        system_prompt = (

            "You are a document question-answering assistant. "

            "Answer the user's question using the retrieved document "

            "evidence as the primary source of truth. "

            "Do not invent facts that are not supported by the document. "

            "If the document does not contain enough information, "

            "clearly say so."

        )



        user_prompt = (

            f"Conversation history:\n{history}\n\n"

            f"User question:\n{state.query}\n\n"

            f"Retrieved document evidence:\n{context}"

        )



        return self._generate_with_available_providers(

            state=state,

            system_prompt=system_prompt,

            user_prompt=user_prompt,

            context=context,

        )



    # ------------------------------------------------------------------



    # DUAL PROVIDER GENERATION



    # ------------------------------------------------------------------



    def _generate_with_available_providers(

        self,

        *,

        state: AgentState,

        system_prompt: str,

        user_prompt: str,

        context: str = "",

    ) -> AgentState:

        """



        Generate using OpenAI and Gemini when available.







        If both providers work:



            OpenAI + Gemini -> synthesis -> final answer







        If only Gemini works:



            Gemini -> final answer







        If only OpenAI works:



            OpenAI -> final answer







        If neither works:



            fallback provider -> final answer



        """



        # Reset provider-specific answers for this generation.



        state.openai_answer = None



        state.gemini_answer = None



        openai_error: str | None = None



        gemini_error: str | None = None



        # --------------------------------------------------------------



        # DUAL PROVIDER MODE



        # --------------------------------------------------------------



        if self._openai_provider is not None and self._gemini_provider is not None:



            # --------------------------------------------------------------



            # Try OpenAI and Gemini in parallel



            # --------------------------------------------------------------



            with ThreadPoolExecutor(max_workers=2) as executor:



                openai_future = executor.submit(

                    self._openai_provider.generate,

                    system_prompt=system_prompt,

                    user_prompt=user_prompt,

                )



                gemini_future = executor.submit(

                    self._gemini_provider.generate,

                    system_prompt=system_prompt,

                    user_prompt=user_prompt,

                )



                try:



                    state.openai_answer = openai_future.result()



                except Exception as exc:



                    openai_error = str(exc)



                    state.openai_answer = None



                try:



                    state.gemini_answer = gemini_future.result()



                except Exception as exc:



                    gemini_error = str(exc)



                    state.gemini_answer = None



            # ----------------------------------------------------------



            # BOTH PROVIDERS SUCCEEDED



            # ----------------------------------------------------------



            if state.openai_answer and state.gemini_answer:



                synthesis_prompt = f"User question:\n{state.query}\n\n"



                if context.strip():



                    synthesis_prompt += f"Retrieved evidence:\n{context}\n\n"



                synthesis_prompt += (

                    f"OpenAI answer:\n{state.openai_answer}\n\n"

                    f"Gemini answer:\n{state.gemini_answer}\n\n"

                    "Compare the two answers and produce one accurate "

                    "final answer for the user. "

                    "Resolve disagreements using the available evidence. "

                    "Do not mention the providers or this synthesis process."

                )



                try:



                    state.answer = self._openai_provider.generate(

                        system_prompt=(

                            "You are a verification and synthesis assistant. "

                            "Combine independent AI answers into one accurate "

                            "final response. "

                            "For document questions, use the retrieved "

                            "evidence as the source of truth."

                        ),

                        user_prompt=synthesis_prompt,

                    )



                except Exception as exc:



                    # If synthesis fails, the OpenAI answer is still usable.



                    state.answer = state.openai_answer



                    state.error = (

                        "Both providers generated answers, but synthesis "

                        f"failed: {exc}"

                    )



                return state



            # ----------------------------------------------------------



            # ONLY GEMINI SUCCEEDED



            # ----------------------------------------------------------



            if state.gemini_answer:



                state.answer = state.gemini_answer



                state.error = (

                    "OpenAI was unavailable, so the answer was generated "

                    "using Gemini."

                )



                return state



            # ----------------------------------------------------------



            # ONLY OPENAI SUCCEEDED



            # ----------------------------------------------------------



            if state.openai_answer:



                state.answer = state.openai_answer



                state.error = (

                    "Gemini was unavailable, so the answer was generated "

                    "using OpenAI."

                )



                return state



            # ----------------------------------------------------------



            # BOTH PROVIDERS FAILED



            # ----------------------------------------------------------



            state.answer = (

                "The configured AI providers are temporarily unavailable. "

                "Please try again shortly."

            )



            state.error = (

                f"OpenAI error: {openai_error}; " f"Gemini error: {gemini_error}"

            )



            return state



        # --------------------------------------------------------------



        # SINGLE PROVIDER / TEST MODE



        # --------------------------------------------------------------



        try:



            state.answer = self._llm_provider.generate(

                system_prompt=system_prompt,

                user_prompt=user_prompt,

            )



        except Exception as exc:



            import logging



            logging.exception("LLM provider generation failed")



            state.answer = (

                "I could not generate an answer because the configured "

                "language model provider is currently unavailable."

            )



            state.error = str(exc)



        return state



    # ------------------------------------------------------------------



    # CALCULATOR



    # ------------------------------------------------------------------



    def _generate_calculator_answer(

        self,

        state: AgentState,

    ) -> AgentState:

        """Evaluate a simple mathematical expression safely."""



        expression = state.query.strip()



        # Remove common calculator wording.



        prefixes = (

            "calculate ",

            "calculator ",

        )



        expression_lower = expression.lower()



        for prefix in prefixes:



            if expression_lower.startswith(prefix):



                expression = expression[len(prefix) :].strip()



                break



        try:



            result = self._safe_calculate(expression)



            state.answer = f"The answer is {result}."



            state.verification_passed = True



            state.verification_reason = (

                "The answer was calculated using the calculator route."

            )



        except (ValueError, TypeError, SyntaxError):



            # If it is not a simple mathematical expression, let the



            # configured LLM explain it instead.



            return self._generate_general_answer(state)



        return state



    @staticmethod

    def _safe_calculate(expression: str) -> float:

        """Safely evaluate basic arithmetic without using eval()."""



        if not expression.strip():



            raise ValueError("Expression cannot be empty.")



        tree = ast.parse(expression, mode="eval")



        def evaluate(node: ast.AST) -> float:



            if isinstance(node, ast.Expression):



                return evaluate(node.body)



            if isinstance(node, ast.Constant):



                if isinstance(node.value, (int, float)):



                    return float(node.value)



                raise ValueError("Only numbers are allowed.")



            if isinstance(node, ast.BinOp):



                left = evaluate(node.left)



                right = evaluate(node.right)



                if isinstance(node.op, ast.Add):



                    return left + right



                if isinstance(node.op, ast.Sub):



                    return left - right



                if isinstance(node.op, ast.Mult):



                    return left * right



                if isinstance(node.op, ast.Div):



                    return left / right



                if isinstance(node.op, ast.Mod):



                    return left % right



                if isinstance(node.op, ast.Pow):



                    return float(left**right)



                raise ValueError("Unsupported mathematical operation.")



            if isinstance(node, ast.UnaryOp):



                operand = evaluate(node.operand)



                if isinstance(node.op, ast.USub):



                    return -operand



                if isinstance(node.op, ast.UAdd):



                    return operand



                raise ValueError("Unsupported unary operation.")



            raise ValueError("Invalid mathematical expression.")



        return evaluate(tree)



    @staticmethod

    def _looks_like_calculation(query: str) -> bool:

        """Determine whether a query looks like a simple calculation."""



        query_without_spaces = query.replace(" ", "")



        if not query_without_spaces:



            return False



        has_digit = any(char.isdigit() for char in query_without_spaces)



        has_operator = any(symbol in query_without_spaces for symbol in "+-*/%")



        # Only treat it as a calculator request if it consists mainly



        # of numbers and arithmetic characters.



        allowed_characters = set("0123456789.+-*/()% ")



        characters_are_allowed = all(char in allowed_characters for char in query)



        return has_digit and has_operator and characters_are_allowed



    # ------------------------------------------------------------------



    # DOCUMENT CONTEXT



    # ------------------------------------------------------------------



    @staticmethod

    def _build_document_context(state: AgentState) -> str:

        """Build readable context from retrieved document chunks."""



        context_parts: list[str] = []



        for index, chunk in enumerate(

            state.retrieved_chunks,

            start=1,

        ):



            text = str(chunk.get("text", "")).strip()



            if not text:



                continue



            context_parts.append(f"[Document chunk {index}]\n{text}")



        return "\n\n".join(context_parts)



    # ------------------------------------------------------------------



    # CONVERSATION HISTORY



    # ------------------------------------------------------------------



    @staticmethod

    def _format_conversation_history(

        state: AgentState,

    ) -> str:

        """Format previous conversation messages for the LLM."""



        if not state.conversation_history:



            return "No previous conversation."



        return "\n".join(

            f"{message.role.capitalize()}: {message.content}"

            for message in state.conversation_history

        )



    # ------------------------------------------------------------------



    # VERIFIED RAG SYNTHESIS



    # ------------------------------------------------------------------



    def _synthesize_verified_answer(

        self,

        *,

        state: AgentState,

        context: str,

    ) -> str:

        """Compare both provider answers and produce one final answer."""



        if not state.openai_answer:



            raise ValueError("OpenAI answer is required for synthesis.")



        if not state.gemini_answer:



            raise ValueError("Gemini answer is required for synthesis.")



        if self._openai_provider is None:



            raise ValueError("OpenAI provider is required for synthesis.")



        verifier_system_prompt = (

            "You are the verification and synthesis agent for a document "

            "question-answering system. Your job is to compare two "

            "independent answers against the retrieved document evidence "

            "and produce one accurate final answer.\n\n"

            "Rules:\n"

            "1. Use the retrieved document evidence as the source of truth.\n"

            "2. Do not add information that is not supported by the evidence.\n"

            "3. If OpenAI and Gemini agree and the evidence supports them, "

            "produce a concise unified answer.\n"

            "4. If they disagree, determine which claim is supported by "

            "the evidence and use only the supported claim.\n"

            "5. If the evidence does not resolve the disagreement, "

            "explicitly say that the document does not provide enough "

            "information.\n"

            "6. Do not mention OpenAI, Gemini, models, or this verification "

            "process in the final answer.\n"

            "7. Return only the final answer for the user."

        )



        verifier_user_prompt = (

            f"Question:\n{state.query}\n\n"

            f"Retrieved document evidence:\n{context}\n\n"

            f"OpenAI answer:\n{state.openai_answer}\n\n"

            f"Gemini answer:\n{state.gemini_answer}\n\n"

            "Compare the two answers against the evidence and provide the "

            "single final answer."

        )



        return self._openai_provider.generate(

            system_prompt=verifier_system_prompt,

            user_prompt=verifier_user_prompt,

        )



    # ------------------------------------------------------------------



    # VERIFIER



    # ------------------------------------------------------------------



    def verify(self, state: AgentState) -> AgentState:

        """Verify the generated answer."""



        if not state.answer:



            state.verification_passed = False



            state.verification_reason = "No answer was generated."



            return state



        # General AI answers do not require document verification.



        if state.route != "rag":



            state.verification_passed = True



            state.verification_reason = (

                "The request did not require document grounding."

            )



            return state



        if not state.retrieved_chunks:



            state.verification_passed = False



            state.verification_reason = "No supporting documents were retrieved."



            return state



        context = " ".join(

            chunk["text"] for chunk in state.retrieved_chunks if chunk.get("text")

        )



        if not context.strip():



            state.verification_passed = False



            state.verification_reason = "Retrieved chunks contain no text."



            return state



        # Production mode with both providers.



        if self._openai_provider is not None and self._gemini_provider is not None:



            # Both providers succeeded and synthesis was completed.



            if state.openai_answer and state.gemini_answer:



                state.verification_passed = True



                state.verification_reason = (

                    "The final answer was synthesized by comparing "

                    "independent OpenAI and Gemini responses against the "

                    "retrieved document evidence."

                )



                return state



            # Only Gemini succeeded.



            if state.gemini_answer:



                state.verification_passed = False



                state.verification_reason = (

                    "The answer is grounded in retrieved document evidence, "

                    "but OpenAI was unavailable, so cross-provider "

                    "verification was not completed."

                )



                return state



            # Only OpenAI succeeded.



            if state.openai_answer:



                state.verification_passed = False



                state.verification_reason = (

                    "The answer is grounded in retrieved document evidence, "

                    "but Gemini was unavailable, so cross-provider "

                    "verification was not completed."

                )



                return state



            # Both providers failed.



            state.verification_passed = False



            state.verification_reason = "The configured AI providers were unavailable."



            return state



        # Test/backward-compatible single-provider mode.



        state.verification_passed = True



        state.verification_reason = "Answer has supporting retrieved context."



        return state
