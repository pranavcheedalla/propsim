import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("PropSim UI crashed:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="tab-content">
          <div className="result-card">
            <h3>Something went wrong</h3>
            <p className="muted">
              {this.state.error.message || "An unexpected error occurred."} Try switching tabs or reloading the
              page.
            </p>
            <button type="button" onClick={() => this.setState({ error: null })}>
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
