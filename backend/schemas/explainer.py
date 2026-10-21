"""Bounded Solo Explainer contracts shared by proposal, review, layout and render."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
PlainText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=800)]
RevisionHash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Aspect = Literal["16:9", "9:16"]
Gesture = Literal["calm", "talk", "point-left", "point-right", "emphasize", "count-1", "count-2", "count-3", "think", "wave"]
LockGroup = Literal["content", "visual", "gestures", "layout_16_9", "layout_9_16"]


class StrictModel(BaseModel):
    """A finite schema: unrecognized provider fields never become executable render payloads."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, strict=True)

    @field_validator("*", mode="after")
    @classmethod
    def no_executable_markup(cls, value: object) -> object:
        if isinstance(value, (list, tuple)):
            for item in value:
                cls.no_executable_markup(item)
        if isinstance(value, str) and any(token in value.lower() for token in
                                          ("<script", "<svg", "<iframe", "javascript:", "<!doctype", "<html")):
            raise ValueError("Use plain text and the supported diagram templates, not executable markup.")
        return value


class TokenAnchor(StrictModel):
    """A boundary between spoken tokens; end anchors are exclusive."""

    line_id: Identifier
    token_index: int = Field(ge=0, le=10000)


class NormalizedRect(StrictModel):
    """Rectangle in normalized frame/image coordinates."""

    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    width: float = Field(gt=0, le=1, allow_inf_nan=False)
    height: float = Field(gt=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def within_canvas(self) -> "NormalizedRect":
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("The rectangle must fit inside its canvas.")
        return self


class AssetReference(StrictModel):
    """Pinned library asset identity, never an arbitrary file path or network URL."""

    asset_id: Identifier
    version: int = Field(ge=1)
    content_hash: RevisionHash | None = None


class PhotoVisual(StrictModel):
    """A photo selected by owner or an external-AI prompt awaiting import."""

    kind: Literal["photo"]
    asset: AssetReference | None = None
    prompt: str = Field(default="", max_length=1600)
    caption: str = Field(default="", max_length=180)
    fit: Literal["contain", "cover"] = "contain"
    important_regions: list[NormalizedRect] = Field(default_factory=list, max_length=12)


class DiagramNode(StrictModel):
    """One labeled node within a fixed renderer template."""

    id: Identifier
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    detail: str = Field(default="", max_length=180)


class DiagramEdge(StrictModel):
    """A reference between existing node IDs."""

    source: Identifier
    target: Identifier
    label: str = Field(default="", max_length=60)


class DiagramVisual(StrictModel):
    """Finite steps/comparison/cause-effect diagram; no user-supplied SVG/HTML."""

    kind: Literal["diagram"]
    template: Literal["steps", "comparison", "cause_effect"]
    title: str = Field(default="", max_length=120)
    nodes: list[DiagramNode] = Field(min_length=2, max_length=6)
    edges: list[DiagramEdge] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def valid_graph(self) -> "DiagramVisual":
        ids = {node.id for node in self.nodes}
        if len(ids) != len(self.nodes):
            raise ValueError("Diagram node IDs must be unique.")
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids or edge.source == edge.target:
                raise ValueError("Diagram edges must reference two different existing nodes.")
        return self


class TextCardVisual(StrictModel):
    """Short title and bullets that the shared renderer can measure before approval."""

    kind: Literal["text_card"]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    bullets: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]] = Field(
        default_factory=list, max_length=5,
    )
    emphasis: str = Field(default="", max_length=80)


class ActivityVisual(StrictModel):
    """Phase 55 (ENH-037): an approved Activity Library picture shown full-frame behind the presenter."""

    kind: Literal["activity"]
    activity_id: Identifier
    caption: str = Field(default="", max_length=180)


class SceneReference(StrictModel):
    """Phase 55: the Scene Library place behind the presenter for one segment (its plate is pinned at approval)."""

    scene_id: Identifier


Visual = Annotated[PhotoVisual | DiagramVisual | TextCardVisual | ActivityVisual, Field(discriminator="kind")]


class PresenterPlacement(StrictModel):
    """Presenter position and uniform frame-relative height; collision checks happen in the layout service."""

    anchor: Literal["left", "right", "center"]
    x: float = Field(ge=0, le=1, allow_inf_nan=False)
    y: float = Field(ge=0, le=1, allow_inf_nan=False)
    height: float = Field(default=0.22, ge=0.12, le=0.38, allow_inf_nan=False)


class SegmentLayout(StrictModel):
    """Per-aspect solution, including motion endpoints validated as one path."""

    presenter: PresenterPlacement
    illustration: NormalizedRect
    motion_from: PresenterPlacement | None = None
    transition: Literal["cut", "ease", "slide"] = "ease"
    transition_seconds: float = Field(default=0.4, ge=0, le=1.5)
    rules_version: int = Field(default=1, ge=1)


class GestureCue(StrictModel):
    """Gesture anchored to real speech tokens rather than estimated AI seconds."""

    at: TokenAnchor
    gesture: Gesture = "talk"


class SegmentLocks(StrictModel):
    """Owner edits are protected individually when a proposal is regenerated."""

    content: bool = False
    visual: bool = False
    gestures: bool = False
    layout_16_9: bool = False
    layout_9_16: bool = False


class ExplainerSegment(StrictModel):
    """A contiguous script span, its illustration and the two independent layouts."""

    id: Identifier
    intent: PlainText
    line_ids: list[Identifier] = Field(min_length=1, max_length=200)
    start: TokenAnchor
    end: TokenAnchor
    visual: Visual
    scene: SceneReference | None = None
    gestures: list[GestureCue] = Field(default_factory=list, max_length=30)
    layouts: dict[Aspect, SegmentLayout] = Field(default_factory=dict, max_length=2)
    locks: SegmentLocks = Field(default_factory=SegmentLocks)
    source_notes: str = Field(default="", max_length=1200)
    needs_fact_review: bool = True

    @model_validator(mode="after")
    def anchor_membership(self) -> "ExplainerSegment":
        if len(set(self.line_ids)) != len(self.line_ids):
            raise ValueError("Segment line IDs must be unique and ordered as in the script.")
        if self.start.line_id not in self.line_ids or self.end.line_id not in self.line_ids:
            raise ValueError("Both anchors must belong to the segment's lines.")
        if self.start.line_id == self.end.line_id and self.end.token_index <= self.start.token_index:
            raise ValueError("A segment must contain at least one spoken token.")
        if any(cue.at.line_id not in self.line_ids for cue in self.gestures):
            raise ValueError("Gesture anchors must belong to the segment's lines.")
        return self


class PresenterReference(StrictModel):
    """The precise profile/front pack consumed by an approved render."""

    speaker_id: Identifier
    profile_id: Identifier
    identity_version: int = Field(ge=1)
    front_pack_revision: RevisionHash | None = None
    asset_ids: list[Identifier] = Field(default_factory=list, max_length=21)


class ExplainerPlan(StrictModel):
    """Versioned content/layout plan; approval also requires DB/timing/assets validation."""

    schema_version: Literal[1] = 1
    project_id: Identifier
    revision: int = Field(ge=1)
    status: Literal["draft", "approved", "stale"] = "draft"
    source_fingerprint: RevisionHash
    presenter: PresenterReference
    segments: list[ExplainerSegment] = Field(min_length=1, max_length=60)
    aspects: list[Aspect] = Field(default_factory=lambda: ["16:9", "9:16"], min_length=1, max_length=2)
    issues: list[Annotated[str, StringConstraints(max_length=500)]] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique_ids_and_aspects(self) -> "ExplainerPlan":
        if len({segment.id for segment in self.segments}) != len(self.segments):
            raise ValueError("Segment IDs must be unique.")
        if len(set(self.aspects)) != len(self.aspects):
            raise ValueError("Output aspects must be unique.")
        return self


class ExplainerPlanPatch(StrictModel):
    """Owner edits carry the revision they were made against; server owns approval and fingerprint."""

    expected_revision: int = Field(ge=1)
    expected_source_fingerprint: RevisionHash
    segments: list[ExplainerSegment] = Field(min_length=1, max_length=60)
    aspects: list[Aspect] = Field(default_factory=lambda: ["16:9", "9:16"], min_length=1, max_length=2)
    unlock_fields: dict[Identifier, list[LockGroup]] = Field(default_factory=dict, max_length=60)

    @model_validator(mode="after")
    def bounded_unlocks(self) -> "ExplainerPlanPatch":
        if len({segment.id for segment in self.segments}) != len(self.segments):
            raise ValueError("Segment IDs must be unique.")
        if len(set(self.aspects)) != len(self.aspects):
            raise ValueError("Output aspects must be unique.")
        if any(len(groups) > 5 or len(set(groups)) != len(groups) for groups in self.unlock_fields.values()):
            raise ValueError("Choose each lock group at most once per segment.")
        if set(self.unlock_fields) - {segment.id for segment in self.segments}:
            raise ValueError("Unlock fields must refer to segments in this edit.")
        return self


class ExplainerApproval(StrictModel):
    """Explicit approval of one reviewed version."""

    expected_revision: int = Field(ge=1)
    source_fingerprint: RevisionHash


class ExplainerProposalRequest(StrictModel):
    """A revision-aware durable proposal request; zero means no plan exists yet."""

    expected_revision: int = Field(ge=0)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=100)


class ProposedExplainerSegment(StrictModel):
    """Provider data excludes owner locks, approval, revision and geometry."""

    id: Identifier
    intent: PlainText
    line_ids: list[Identifier] = Field(min_length=1, max_length=200)
    start: TokenAnchor
    end: TokenAnchor
    visual: Visual
    scene: SceneReference | None = None
    gestures: list[GestureCue] = Field(default_factory=list, max_length=30)
    source_notes: str = Field(default="", max_length=1200)


class ExplainerProposal(StrictModel):
    """Finite content-only response from the structured AI gateway."""

    segments: list[ProposedExplainerSegment] = Field(min_length=1, max_length=60)

    @model_validator(mode="after")
    def unique_segment_ids(self) -> "ExplainerProposal":
        if len({segment.id for segment in self.segments}) != len(self.segments):
            raise ValueError("Segment IDs must be unique.")
        return self
