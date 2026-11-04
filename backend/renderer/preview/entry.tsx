import React from "react";
import {createRoot} from "react-dom/client";
import type {PlayerRef} from "@remotion/player";
import {PreviewEditor} from "./PreviewEditor";
import {episodeInputPropsSchema,type EpisodeInputProps} from "../src/types";
import {sampleProps} from "../src/sampleShort";

declare global {interface Window {ShortsSample:{props:typeof sampleProps};SoloPreview:{mount:(node:HTMLElement,props:EpisodeInputProps)=>{update:(props:EpisodeInputProps)=>void;seek:(frame:number)=>void;destroy:()=>void}}}}
window.SoloPreview={mount(node,initial){
  const root=createRoot(node);let player:PlayerRef|null=null;
  const update=(data:EpisodeInputProps)=>{const props=episodeInputPropsSchema.parse(data);root.render(<PreviewEditor props={props} onReady={value=>{player=value;}}/>);};
  update(initial);
  return {update,seek(frame){player?.pause();player?.seekTo(Math.max(0,Math.floor(frame)));},destroy(){player?.pause();root.unmount();player=null;}};
}};
// Phase 68 (ENH-050): silent sample props of a Shorts template for the Shorts batch page
window.ShortsSample={props:sampleProps};
