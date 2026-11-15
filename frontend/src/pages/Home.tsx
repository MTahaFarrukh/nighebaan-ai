import { Link } from "react-router-dom";

const features = [
  {
    number: "01",
    title: "Check more than text",
    description:
      "Review Roman Urdu messages and static URLs, or extract text from images, PDFs, voice notes and short videos.",
    link: "/analyze",
    action: "Open analyzer",
  },
  {
    number: "02",
    title: "See the evidence",
    description:
      "Model predictions, risk levels and expert-rule IDs make the warning easier to review—not a verdict to follow blindly.",
    link: "/models",
    action: "Explore Model Lab",
  },
  {
    number: "03",
    title: "Keep judgment yours",
    description:
      "Inspect high-risk metadata without turning the app into a transcript viewer. A low score never guarantees safety.",
    link: "/about",
    action: "Read our safeguards",
  },
];

export default function Home() {
  return (
    <div className="home-page">
      <section className="landing-hero" aria-labelledby="landing-title">
        <div className="landing-copy">
          <p className="hero-kicker">
            <span className="hero-kicker-dot" aria-hidden="true" />
            A LOCAL, EXPLAINABLE SAFETY ASSISTANT
          </p>
          <h1 id="landing-title">
            Pause. Check.
            <br />
            Move with <span>confidence.</span>
          </h1>
          <p className="hero-description">
            Check Roman Urdu messages, links and media for warning signs. Review
            the explanation, then decide what to do with a clearer picture.
          </p>
          <div className="hero-actions">
            <Link className="primary hero-primary" to="/analyze">
              Start an analysis <span aria-hidden="true">↗</span>
            </Link>
            <Link className="hero-secondary" to="/about">
              How it works <span aria-hidden="true">→</span>
            </Link>
          </div>
          <div className="hero-assurances" aria-label="Product principles">
            <span>
              <i aria-hidden="true">✓</i> Local processing
            </span>
            <span>
              <i aria-hidden="true">✓</i> Links are never opened
            </span>
            <span>
              <i aria-hidden="true">✓</i> Human judgment first
            </span>
          </div>
        </div>

        <div className="hero-art" aria-hidden="true">
          <div className="hero-scene-glow hero-scene-glow-one" />
          <div className="hero-scene-glow hero-scene-glow-two" />
          <div className="hero-glass-card hero-glass-card-back">
            <span className="hero-card-index">01 / INPUT</span>
            <div className="hero-card-sample">
              <span className="sample-icon">Aa</span>
              <span className="sample-lines">
                <i />
                <i />
                <i />
              </span>
            </div>
            <span className="hero-card-caption">Text · URL · Media</span>
          </div>
          <div className="hero-glass-card hero-glass-card-front">
            <div className="hero-glass-topline">
              <span className="hero-window-label">
                <i />
                ILLUSTRATIVE FLOW
              </span>
              <span className="hero-window-dots">
                <i />
                <i />
                <i />
              </span>
            </div>
            <div className="hero-flow-title">
              <div className="hero-flow-emblem">
                <svg viewBox="0 0 120 136" fill="none">
                  <path
                    d="M60 7 105 24v35c0 31-18 55-45 69C33 114 15 90 15 59V24L60 7Z"
                    stroke="currentColor"
                    strokeWidth="3"
                  />
                  <path
                    d="m41 67 13 13 27-29"
                    stroke="currentColor"
                    strokeWidth="5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <div>
                <p>THE NIGEHBAAN FLOW</p>
                <strong>Signals, made clear.</strong>
                <span>Human judgment stays in control.</span>
              </div>
            </div>
            <div className="hero-scan-track">
              <span />
            </div>
            <div className="hero-flow-steps">
              <span>INPUT</span>
              <i />
              <span>CHECKS</span>
              <i />
              <span>INSIGHT</span>
            </div>
            <div className="hero-waveform" aria-hidden="true">
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
            </div>
          </div>
          <div className="hero-glass-card hero-glass-card-side">
            <span className="hero-side-icon">✦</span>
            <span>
              <strong>Explainable</strong>
              <small>Model + expert rules</small>
            </span>
          </div>
        </div>
      </section>

      <section className="landing-features" aria-labelledby="features-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">A CLEARER WAY TO CHECK</p>
            <h2 id="features-title">Protection should make sense.</h2>
          </div>
          <p className="muted">
            One place to inspect signals, understand the reasoning and stay in
            control.
          </p>
        </div>
        <div className="landing-feature-grid">
          {features.map((feature) => (
            <article className="landing-feature-card" key={feature.number}>
              <span className="feature-number">{feature.number}</span>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
              <Link to={feature.link}>
                {feature.action} <span aria-hidden="true">→</span>
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-process" aria-labelledby="process-title">
        <div className="process-heading">
          <p className="eyebrow">THREE SIMPLE STEPS</p>
          <h2 id="process-title">From a message to a more informed choice.</h2>
        </div>
        <div className="process-grid">
          <article>
            <span className="process-index">01</span>
            <h3>Bring a signal</h3>
            <p>
              Paste a message or URL, or choose a supported image, PDF, audio or
              video file.
            </p>
          </article>
          <article>
            <span className="process-index">02</span>
            <h3>Review the evidence</h3>
            <p>
              Local models and expert rules look for indicators. Submitted URLs
              are analyzed statically, never opened.
            </p>
          </article>
          <article>
            <span className="process-index">03</span>
            <h3>Choose your next step</h3>
            <p>
              Read the risk explanation, verify urgent requests independently
              and make the final decision yourself.
            </p>
          </article>
        </div>
      </section>

      <section className="landing-cta">
        <div>
          <p className="eyebrow">STAY CURIOUS. STAY IN CONTROL.</p>
          <h2>Not sure about a message?</h2>
          <p className="muted">
            Start with a synthetic example or analyze something you are
            authorized to check.
          </p>
        </div>
        <Link className="primary hero-primary" to="/analyze">
          Go to Analyze <span aria-hidden="true">↗</span>
        </Link>
      </section>
      <p className="landing-disclaimer">
        Nigehbaan AI offers decision support, not a guarantee. A low-risk result
        does not prove that content is safe.
      </p>
    </div>
  );
}
