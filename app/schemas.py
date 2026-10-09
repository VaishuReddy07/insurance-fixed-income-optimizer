from pydantic import BaseModel, Field

class OptimizeRequest(BaseModel):
    target_duration: float = Field(5.0, ge=0.5, le=15)
    duration_tolerance: float = Field(1.0, ge=0.1, le=5)
    min_rating: str = "BBB"
    max_weight: float = Field(0.08, gt=0, le=0.25)
    max_issuer_weight: float = Field(0.15, gt=0.05, le=0.4)
    min_liquidity: float = Field(0.35, ge=0, le=1)
    min_esg_score: float = Field(0, ge=0, le=100)
    exclude_energy: bool = False
    risk_aversion: float = Field(4.0, ge=0, le=30)

