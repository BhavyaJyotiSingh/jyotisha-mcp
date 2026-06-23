"""
Consensus Engine — Layer K

Combines predictions from multiple astrological schools (Parashara, Jaimini, KP)
and generates a unified consensus report with confidence scoring.
"""


from jyotisha.models.schemas import Chart, SchoolResult, ConsensusPrediction
from jyotisha.schools.parashara import ParasharaModule
from jyotisha.schools.jaimini import JaiminiModule
from jyotisha.schools.kp import KPModule

class ConsensusEngine:
    """
    Coordinates multi-school predictions.
    """
    
    def __init__(self):
        self.parashara = ParasharaModule()
        self.jaimini = JaiminiModule()
        self.kp = KPModule()
        
        # Define base confidence weights for schools (customizable)
        self.weights = {
            "Parashara": 0.5,
            "Jaimini": 0.3,
            "Krishnamurti Paddhati (KP)": 0.2
        }

    def generate_consensus(self, chart: Chart, question: str) -> ConsensusPrediction:
        """
        Takes a specific question/event type (e.g., "marriage", "career")
        and queries each school for a prediction.
        """
        
        # 1. Gather results from each school
        school_results = []
        
        # Parashara Result
        p_res = self.parashara.predict(chart, question=question)
        school_results.append(p_res)
        
        # Jaimini Result
        j_res = self.jaimini.predict(chart, question=question)
        school_results.append(j_res)
        
        # KP Result
        k_res = self.kp.predict(chart, question=question)
        school_results.append(k_res)
        
        # 2. Calculate weighted consensus
        total_weight = 0.0
        weighted_score = 0.0
        combined_reasoning = ""
        
        for res in school_results:
            weight = self.weights.get(res.school, 0.3)
            if res.confidence > 0:
                weighted_score += (res.confidence * weight)
                total_weight += weight
                combined_reasoning += f"[{res.school}]: {res.answer} (Confidence: {res.confidence})\n"
                if res.reasoning:
                    combined_reasoning += f"  Reasoning: {res.reasoning}\n"
                    
        final_confidence = (weighted_score / total_weight) if total_weight > 0 else 0.0
        
        final_conclusion = "Unable to reach a consensus."
        if final_confidence > 0.7:
            final_conclusion = "Strong indicators present across multiple schools."
        elif final_confidence > 0.4:
            final_conclusion = "Mixed or moderate indicators."
            
        return ConsensusPrediction(
            question=question,
            consensus_answer=final_conclusion,
            consensus_confidence=round(final_confidence, 2),
            school_results=school_results,
            explanation=combined_reasoning.strip()
        )
