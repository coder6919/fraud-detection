import { Route, Routes } from "react-router-dom";
import Nav from "./components/Nav.jsx";
import OverviewGraph from "./views/OverviewGraph.jsx";
import RingDetailView from "./views/RingDetailView.jsx";
import AccountView from "./views/AccountView.jsx";

export default function App() {
  return (
    <>
      <Nav />
      <Routes>
        <Route path="/" element={<OverviewGraph />} />
        <Route path="/rings/:ringId" element={<RingDetailView />} />
        <Route path="/account/:accountId" element={<AccountView />} />
      </Routes>
    </>
  );
}
