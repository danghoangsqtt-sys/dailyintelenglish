import React from "react";
import { Img, useVideoConfig } from "remotion";
import { resolvedMedia } from "./Presenter";
import type { GeometrySegment, SoloSegment } from "./soloTypes";
import type { Aspect } from "./explainerLayout";

/** Same rule as the backend text metrics: steps/cause-effect already show consecutive order, so only other edges get a line. */
export function shownEdges(visual: {template?: string; nodes: {id: string}[]; edges?: {source: string; target: string; label?: string}[]}) {
  const order = visual.nodes.map(node => node.id), implied = visual.template === "steps" || visual.template === "cause_effect";
  return (visual.edges ?? []).filter(edge => edge.label || !implied || !order.includes(edge.source) || !order.includes(edge.target)
    || order.indexOf(edge.target) !== order.indexOf(edge.source) + 1);
}

export function ExplainerVisual({segment, proof, aspect, progress=1}: {segment: SoloSegment; proof: GeometrySegment; aspect: Aspect; progress?:number}) {
  const {width, height} = useVideoConfig();
  const box = segment.layouts[aspect].illustration, visual = segment.visual, text = proof.text;
  if (visual.kind === "activity") return null;  // drawn full-frame by the stage behind the presenter
  const style: React.CSSProperties = {position:"absolute", left:box.x*width, top:box.y*height, width:box.width*width, height:box.height*height,
    boxSizing:"border-box", color:"#F3F4E6", fontFamily:"Arial,sans-serif", padding:text.padding, borderRadius:20,
    background:"linear-gradient(145deg,rgba(23,63,51,0.86),rgba(9,32,27,0.82))", border:"1px solid rgba(163,200,150,0.75)",
    boxShadow:"0 18px 40px rgba(0,0,0,0.35)", overflowWrap:"anywhere", whiteSpace:"pre-wrap"};
  if (visual.kind === "photo") return <div data-solo-visual="photo" style={{...style,padding:0,background:"#0E241E"}}>
    {/* URL is supplied through the scoped bridge, never user-supplied HTML or a filesystem path. */}
    {(segment as SoloSegment & {photoUrl?: string}).photoUrl ? <Img src={resolvedMedia((segment as SoloSegment & {photoUrl?: string}).photoUrl!)} style={{width:"100%",height:"100%",objectFit:visual.fit ?? "contain",borderRadius:20}} />
      : <div style={{padding:text.padding,fontSize:text.font}}>Import this illustration before approval.</div>}
  </div>;
  if (visual.kind !== "text_card" && visual.kind !== "diagram") return null;  // the VOX kinds are drawn by VoxVisual
  return <div data-solo-visual={visual.kind} style={style}>
    {visual.title ? <div style={{fontSize:text.titleFont,lineHeight:1.25,fontWeight:750,marginBottom:text.gap}}>{visual.title}</div> : null}
    {visual.kind === "text_card" ? <>
      {(visual.bullets ?? []).map((bullet,i)=><div key={i} style={{opacity:progress>=i/Math.max(1,visual.bullets?.length??1)?1:0,fontSize:text.font,lineHeight:1.3,marginBottom:text.gap}}>• {bullet}</div>)}
      {visual.emphasis ? <div style={{fontSize:text.font,lineHeight:1.3,color:"#F1D16E"}}>{visual.emphasis}</div> : null}
    </> : <><div style={{display:"grid",gridTemplateColumns:`repeat(${text.columns}, minmax(0,1fr))`,gap:text.gap}}>
      {visual.nodes.map((node,i)=><div key={node.id} style={{opacity:progress>=i/visual.nodes.length?1:0,padding:text.gap,border:"1px solid #A3B992",borderRadius:12,fontSize:text.font,lineHeight:1.3,position:"relative"}}>
        <strong style={{color:"#F1D16E"}}>{visual.template === "steps" ? `${i+1}. ` : ""}{node.label}</strong>
        {node.detail ? <div>{node.detail}</div> : null}
        {visual.template === "cause_effect" && i < visual.nodes.length-1 ? <span style={{position:"absolute",right:2,bottom:0,fontSize:text.font}}>→</span> : null}
      </div>)}
    </div>{shownEdges(visual).map((edge,i)=><div key={i} style={{fontSize:text.font,lineHeight:1.3,marginTop:text.gap}}>
      {visual.nodes.find(n=>n.id===edge.source)?.label} → {visual.nodes.find(n=>n.id===edge.target)?.label}{edge.label?`: ${edge.label}`:""}
    </div>)}</>}
  </div>;
}
