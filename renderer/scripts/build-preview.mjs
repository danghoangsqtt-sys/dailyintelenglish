import {build} from "esbuild";
import {fileURLToPath} from "node:url";
import path from "node:path";
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),"..");
await build({entryPoints:[path.join(root,"preview/entry.tsx")],bundle:true,minify:true,format:"iife",platform:"browser",target:"chrome120",
  banner:{js:'window.remotion_staticBase="/static";'},
  outfile:path.join(root,"../frontend/static/solo-preview/player.js"),define:{"process.env.NODE_ENV":'"production"'},logLevel:"info"});
