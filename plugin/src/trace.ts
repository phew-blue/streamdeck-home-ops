// plugin/src/trace.ts
//
// A file the plugin can be diagnosed from.
//
// plugin.ts sets streamDeck.logger.setLevel("trace"), and under Stream Deck
// 7.5 that produces nothing at all -- the plugin's own logs/ directory is never
// created. With no log, a plugin that starts, connects and then shows blank
// tiles gives you no way to tell apart the three things that cause it: events
// not arriving, settings not arriving, or the HTTP call failing. Diagnosing
// exactly that took several wrong guesses; this file is the cheap way to not
// repeat them.
//
// The log sits beside the installed plugin rather than at a fixed path, so it
// works wherever Stream Deck put the plugin. Appends are synchronous and
// best-effort: a diagnostic that throws inside an event handler would break the
// thing it is diagnosing.
import { appendFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const PATH = fileURLToPath(new URL("../plugin-trace.log", import.meta.url));

export function trace(msg: string): void {
  try {
    appendFileSync(PATH, `${new Date().toISOString()} ${msg}\n`);
  } catch {
    // Nothing useful to do here: this is the logging path.
  }
}
