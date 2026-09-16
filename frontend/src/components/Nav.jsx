import { Link } from "react-router-dom";
import SearchBar from "./SearchBar.jsx";
import styles from "./Nav.module.css";

export default function Nav() {
  return (
    <nav className={styles.nav}>
      <Link to="/" className={styles.brand}>Fraud Ring Detection</Link>
      <SearchBar />
    </nav>
  );
}
