import React from "react";
import "./Header.css";
import logo from "assets/FinVox-AI-logo.jpg";

const Header: React.FC = () => {
  return (
    <header className="fv-header" role="banner" aria-label="FinVox AI Banking Assistant">
      <div className="fv-header-inner">
        <div className="fv-brand">
          <img
            src={logo}
            alt="FinVox AI logo"
            className="fv-logo"
            width={56}
            height={56}
            loading="lazy"
            decoding="async"
          />

          <div className="fv-title-wrap">
            <h1 className="fv-title">
              FinVox <span className="fv-accent">AI</span>
            </h1>
            <p className="fv-subtitle">Banking Assistant</p>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
