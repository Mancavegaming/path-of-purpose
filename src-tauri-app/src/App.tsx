import { createSignal, Match, Switch } from "solid-js";
import Sidebar, { type Page } from "./components/Sidebar";
import DecodePage from "./pages/DecodePage";
import DeltaPage from "./pages/DeltaPage";
import "./styles.css";

function App() {
  const [page, setPage] = createSignal<Page>("decode");

  return (
    <div class="app-layout">
      <Sidebar page={page} setPage={setPage} />
      <main class="content">
        <Switch>
          <Match when={page() === "decode"}>
            <DecodePage />
          </Match>
          <Match when={page() === "delta"}>
            <DeltaPage />
          </Match>
        </Switch>
      </main>
    </div>
  );
}

export default App;
