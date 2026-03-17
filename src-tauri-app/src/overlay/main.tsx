/* @refresh reload */
import { render } from "solid-js/web";
import OverlayApp from "./OverlayApp";
import "./overlay.css";

const root = document.getElementById("overlay-root");

if (root) {
  render(() => <OverlayApp />, root);
}
