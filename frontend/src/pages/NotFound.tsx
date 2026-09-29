import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="stack">
      <h1>Page not found</h1>
      <p>
        <Link to="/">Go back to the start</Link>
      </p>
    </div>
  );
}
