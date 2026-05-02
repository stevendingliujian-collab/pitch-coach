from pydantic import BaseModel


class TalkingPoint(BaseModel):
    point: str
    is_emphasis: bool = False


class EmphasisMark(BaseModel):
    text: str
    reason: str


class PlanPageResponse(BaseModel):
    id: int
    page_number: int
    page_title: str | None
    page_content_summary: str | None
    page_thumbnail_url: str | None
    importance_level: int
    talking_points: list
    suggested_duration: int
    emphasis_marks: list | None
    bid_req_mapping: list | None
    transition_hint: str | None
    opening_templates: list | None
    closing_templates: list | None
    is_manually_edited: bool

    model_config = {"from_attributes": True}


class PlanPageUpdate(BaseModel):
    importance_level: int | None = None
    talking_points: list | None = None
    suggested_duration: int | None = None
    emphasis_marks: list | None = None
    transition_hint: str | None = None


class PitchPlanResponse(BaseModel):
    id: int
    pitch_task_id: int
    ppt_file_id: str
    ppt_file_name: str
    ppt_page_count: int
    global_strategy: str | None
    total_duration_sec: int | None
    predicted_questions: list | None
    competitive_differentiation: list | None
    opening_templates: list | None
    closing_templates: list | None
    status: int
    version: int
    pages: list[PlanPageResponse] = []

    model_config = {"from_attributes": True}


class GeneratePlanRequest(BaseModel):
    pitch_task_id: int
    ppt_file_id: str       # OSS object key after direct upload
    ppt_file_name: str
    bid_requirements: str | None = None
    bid_time_limit: int | None = None


class RegeneratePlanRequest(BaseModel):
    scope: str = "global"  # "global" | "page"
    page_number: int | None = None
    user_instruction: str | None = None
