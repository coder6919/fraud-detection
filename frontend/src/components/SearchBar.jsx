import { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./SearchBar.module.css";

export default function SearchBar() {
  const [value, setValue] = useState("");
  const navigate = useNavigate();

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) navigate(`/account/${trimmed}`);
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input
        className={styles.input}
        type="text"
        placeholder="Look up account id..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button className={styles.button} type="submit">Search</button>
    </form>
  );
}
