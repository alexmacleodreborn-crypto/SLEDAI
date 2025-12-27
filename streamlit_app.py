"""
SledAI — A SLED-style cognitive engine for your project.

Core behaviour:
- Receives a user question.
- Compiles background information in relevant domains.
- Runs a SLED-style coherence loop (Sigma, Z, Divergence).
- Probes with clarification questions if coherence is low.
- Only produces a final answer when internal physics are stable.

Intended usage:
    from sled_ai import SledAI
    ai = SledAI()
    response = ai.run("Explain the connection between gravity and entropy.")
"""

import time
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


# -------------------------------
#  Data structures
# -------------------------------

@dataclass
class BackgroundPacket:
    domain: str
    notes: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0–1
    completeness: float = 0.0  # 0–1


@dataclass
class CoherenceState:
    sigma: float           # internal chaos / entropy
    z: float               # inhibition / logic gate
    divergence: float      # sigma * z
    coherence: float       # 0–1, derived from divergence


@dataclass
class SledAIConfig:
    truth_threshold: float = 0.55  # threshold for safe output
    max_iterations: int = 3        # how many coherence passes before probing
    probing_threshold: float = 0.6 # below this, ask questions
    wake_level: float = 1e-5       # conceptual "birth" sensitivity


# -------------------------------
#  SledAI main class
# -------------------------------

class SledAI:
    def __init__(self, config: Optional[SledAIConfig] = None):
        self.config = config or SledAIConfig()
        self.interaction_count = 0  # "age" in interactions

        # Domains relevant to your project
        self.domains = [
            "language_symbols",
            "geography",
            "relationships_empathy",
            "science_engineering",
            "politics_economics",
            "philosophy",
            "mathematics",
            "computing_logic",
        ]

    # -------------------------------------------------
    #  Public entrypoint
    # -------------------------------------------------
    def run(self, question: str) -> Dict[str, Any]:
        """
        Main cognitive loop. Returns a dict with:
        - 'status': 'probing' | 'answer'
        - 'probing_questions': list[str] (if status='probing')
        - 'answer': str (if status='answer')
        - 'coherence_state': CoherenceState as dict
        - 'background': background packets as plain dicts
        """
        self.interaction_count += 1

        # STEP 1: Domain analysis
        domains = self._detect_domains(question)

        # STEP 2: Background compilation (no user-facing answer yet)
        background = self._compile_background(question, domains)

        # STEP 3: Coherence loop (SLED-style)
        coherence_state = None
        for iteration in range(1, self.config.max_iterations + 1):
            coherence_state = self._compute_coherence(question, background, iteration)

            if coherence_state.coherence >= self.config.truth_threshold:
                break
            else:
                # brief "thinking" delay to simulate internal work
                time.sleep(0.1)

        # STEP 4: Decide: probing or answer
        if coherence_state.coherence < self.config.probing_threshold:
            probing_questions = self._generate_probing_questions(question, domains, background, coherence_state)
            return {
                "status": "probing",
                "probing_questions": probing_questions,
                "coherence_state": self._coherence_to_dict(coherence_state),
                "background": self._background_to_dicts(background),
            }
        else:
            answer = self._generate_answer(question, domains, background, coherence_state)
            return {
                "status": "answer",
                "answer": answer,
                "coherence_state": self._coherence_to_dict(coherence_state),
                "background": self._background_to_dicts(background),
            }

    # -------------------------------------------------
    #  Domain detection
    # -------------------------------------------------
    def _detect_domains(self, question: str) -> List[str]:
        """Rough routing of the question into domains."""
        q = question.lower()
        active = []

        # Language / symbols
        if any(w in q for w in ["word", "language", "symbol", "meaning", "translate"]):
            active.append("language_symbols")

        # Geography
        if any(w in q for w in ["country", "city", "continent", "border", "map", "capital"]):
            active.append("geography")

        # Relationships / empathy
        if any(w in q for w in ["relationship", "friend", "family", "feel", "emotion", "empathy"]):
            active.append("relationships_empathy")

        # Science / engineering
        if any(w in q for w in ["physics", "chemistry", "biology", "engineering", "gravity", "entropy", "force"]):
            active.append("science_engineering")

        # Politics / economics
        if any(w in q for w in ["election", "policy", "government", "inflation", "market", "stock", "economy"]):
            active.append("politics_economics")

        # Philosophy
        if any(w in q for w in ["meaning of life", "ethics", "morality", "consciousness", "free will"]):
            active.append("philosophy")

        # Mathematics
        if any(w in q for w in ["equation", "theorem", "proof", "integral", "derivative", "probability"]):
            active.append("mathematics")

        # Computing / logic
        if any(w in q for w in ["algorithm", "code", "program", "logic", "boolean", "bit", "neural"]):
            active.append("computing_logic")

        # If nothing obvious, assume broad
        if not active:
            active = ["language_symbols"]

        return active

    # -------------------------------------------------
    #  Background compilation (placeholders / hooks)
    # -------------------------------------------------
    def _compile_background(self, question: str, domains: List[str]) -> Dict[str, BackgroundPacket]:
        """
        For now, this uses simple heuristics as stand-ins for real retrieval.
        In your project, this is where you plug in:
        - stock/market data
        - domain-specific databases
        - curated corpora
        """
        background: Dict[str, BackgroundPacket] = {}

        for d in domains:
            packet = BackgroundPacket(domain=d)

            if d == "science_engineering":
                packet.notes.append("Physical theories relevant to the question (e.g., gravity, entropy, thermodynamics).")
                packet.confidence = 0.8
                packet.completeness = 0.7

            elif d == "politics_economics":
                packet.notes.append("Relevant macro and micro economic context, policies, and market interaction logic.")
                packet.confidence = 0.7
                packet.completeness = 0.6

            elif d == "language_symbols":
                packet.notes.append("Key terms, their meanings, and likely intended sense in this question.")
                packet.confidence = 0.75
                packet.completeness = 0.65

            elif d == "mathematics":
                packet.notes.append("Mathematical structures, equations, and known relations that might support the explanation.")
                packet.confidence = 0.7
                packet.completeness = 0.6

            elif d == "computing_logic":
                packet.notes.append("Algorithmic or logical patterns relevant to interpreting or structuring the answer.")
                packet.confidence = 0.7
                packet.completeness = 0.6

            elif d == "relationships_empathy":
                packet.notes.append("Emotional tone, relational impact, and safe framing of the explanation.")
                packet.confidence = 0.7
                packet.completeness = 0.6

            elif d == "geography":
                packet.notes.append("Geographical framing if the question mentions places, borders, or spatial context.")
                packet.confidence = 0.65
                packet.completeness = 0.55

            elif d == "philosophy":
                packet.notes.append("Conceptual, ethical, or metaphysical framing relevant to the question.")
                packet.confidence = 0.7
                packet.completeness = 0.6

            background[d] = packet

        return background

    # -------------------------------------------------
    #  Coherence / SLED physics
    # -------------------------------------------------
    def _compute_coherence(
        self,
        question: str,
        background: Dict[str, BackgroundPacket],
        iteration: int
    ) -> CoherenceState:
        """
        SLED-style synthetic physics:
        - Sigma: internal chaos (higher when domains are many and background weak)
        - Z: inhibition (ability to filter and structure)
        - Divergence: sigma * z
        - Coherence: mapped from divergence (lower divergence → higher coherence)
        """

        # Domain entropy: more domains = more initial chaos
        num_domains = len(background)
        domain_entropy = 0.3 + 0.15 * (num_domains - 1)

        # Background completeness/confidence average
        if background:
            avg_conf = sum(p.confidence for p in background.values()) / num_domains
            avg_comp = sum(p.completeness for p in background.values()) / num_domains
        else:
            avg_conf = 0.0
            avg_comp = 0.0

        # Sigma: starts higher, drops as iterations progress and background solidifies
        sigma_base = domain_entropy * (1.2 - 0.2 * avg_comp)
        sigma = max(0.05, sigma_base * (1.1 - 0.25 * iteration))

        # Z: increases as iteration and confidence grow
        z = min(0.98, 0.3 + 0.4 * avg_conf + 0.1 * iteration)

        divergence = sigma * z

        # Map divergence to coherence score in [0,1]
        # Lower divergence → higher coherence
        coherence = max(0.0, 1.0 - divergence)

        return CoherenceState(
            sigma=sigma,
            z=z,
            divergence=divergence,
            coherence=coherence
        )

    # -------------------------------------------------
    #  Probing questions
    # -------------------------------------------------
    def _generate_probing_questions(
        self,
        question: str,
        domains: List[str],
        background: Dict[str, BackgroundPacket],
        coherence_state: CoherenceState
    ) -> List[str]:
        """
        If coherence is low, ask for structure, not facts.
        The goal: reduce Sigma by clarifying intent & scope.
        """

        qs: List[str] = []

        # General clarification
        qs.append("Can you tell me more about what specifically you want to understand or achieve with this question?")

        # Domain-specific clarifiers
        if "science_engineering" in domains and "mathematics" in domains:
            qs.append("Are you looking for an intuitive explanation, a mathematical description, or both?")

        if "politics_economics" in domains:
            qs.append("Is your focus more on the political decisions, the economic mechanisms, or their interaction?")

        if "relationships_empathy" in domains:
            qs.append("How sensitive or personal is this situation for you, so I can frame my answer appropriately?")

        if "computing_logic" in domains:
            qs.append("Do you want this framed as an algorithm, a logical structure, or a conceptual overview?")

        # If the question is very short or ambiguous
        if len(question.split()) < 6:
            qs.append("Could you add a bit more detail or an example, so I can avoid guessing?")

        return qs

    # -------------------------------------------------
    #  Answer generation (high-level, project-friendly)
    # -------------------------------------------------
    def _generate_answer(
        self,
        question: str,
        domains: List[str],
        background: Dict[str, BackgroundPacket],
        coherence_state: CoherenceState
    ) -> str:
        """
        High-level, domain-aware answer generator.
        In your project, you can route to specialised modules here:
        - stock / market engine
        - physics / engineering module
        - educational explanations
        """

        q = question.lower()

        # Example: gravity/entropy style answer
        if "gravity" in q and "entropy" in q:
            return (
                "Gravity and entropy are linked through how matter, energy, and information organize themselves in spacetime.\n\n"
                "- Entropy measures how many microscopic configurations a system can have.\n"
                "- Gravity curves spacetime according to energy and mass.\n"
                "- Black holes reveal the connection: their entropy is proportional to horizon area.\n"
                "- Gravity shapes structure; entropy drives the arrow of time.\n\n"
                "Together, they describe how the universe evolves."
            )

        # Example: markets/stock phrasing (compatible with your existing app)
        if "stock" in q or "market" in q or "price" in q:
            lines = []
            lines.append("I will treat this as a market-structure and information-flow question, not just a price lookup.")
            lines.append("First, I align on: the instrument, timeframe, and whether you're asking about behaviour, cause, or strategy.")
            lines.append("Then I integrate: known economic context, basic microstructure, and any relevant patterns or anomalies.")
            lines.append("I won't guess on unseen data; I will describe plausible mechanisms and what information would tighten them.")
            return "\n\n".join(lines)

        # Fallback: structured, honest, domain-aware answer
        domain_labels = ", ".join(d.replace("_", " ") for d in domains)
        return (
            "Here is how I will approach your question:\n\n"
            f"1. I interpret it as touching the following domains: {domain_labels}.\n"
            "2. Internally, I have compiled background notes for these domains instead of guessing at an answer.\n"
            "3. My coherence score for this question is high enough to respond without needing more clarification.\n"
            "4. However, the most precise and helpful answer will still depend on whether you prefer a conceptual overview, "
            "a technical breakdown, or a practical, example-driven explanation.\n\n"
            "Tell me your preferred style, and I can specialise the explanation accordingly."
        )

    # -------------------------------------------------
    #  Helpers
    # -------------------------------------------------
    def _coherence_to_dict(self, c: CoherenceState) -> Dict[str, float]:
        return {
            "sigma": c.sigma,
            "z": c.z,
            "divergence": c.divergence,
            "coherence": c.coherence,
        }

    def _background_to_dicts(self, background: Dict[str, BackgroundPacket]) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for domain, packet in background.items():
            out[domain] = {
                "domain": packet.domain,
                "notes": packet.notes,
                "confidence": packet.confidence,
                "completeness": packet.completeness,
            }
        return out


# -------------------------------------------------
#  Quick manual test
# -------------------------------------------------
if __name__ == "__main__":
    ai = SledAI()

    q1 = "Explain the connection between gravity and entropy."
    res1 = ai.run(q1)
    print("\nQUESTION 1:", q1)
    print("STATUS:", res1["status"])
    if res1["status"] == "answer":
        print("\nANSWER:\n", res1["answer"])
    else:
        print("\nPROBING QUESTIONS:")
        for pq in res1["probing_questions"]:
            print("-", pq)

    print("\n" + "="*80 + "\n")

    q2 = "What will happen to this stock price?"
    res2 = ai.run(q2)
    print("QUESTION 2:", q2)
    print("STATUS:", res2["status"])
    if res2["status"] == "answer":
        print("\nANSWER:\n", res2["answer"])
    else:
        print("\nPROBING QUESTIONS:")
        for pq in res2["probing_questions"]:
            print("-", pq)
