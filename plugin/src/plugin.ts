// plugin/src/plugin.ts
import streamDeck from "@elgato/streamdeck";
import { StatusAction } from "./status-action.js";
import { ClusterAction } from "./cluster-action.js";
import { NodeAction } from "./node-action.js";

streamDeck.logger.setLevel("trace");
streamDeck.actions.registerAction(new StatusAction());
streamDeck.actions.registerAction(new ClusterAction());
streamDeck.actions.registerAction(new NodeAction());
streamDeck.connect();
