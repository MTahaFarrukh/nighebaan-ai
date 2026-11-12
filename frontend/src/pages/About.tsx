import { PageHeader } from "../components/ui";
export default function About() {
  return (
    <>
      <PageHeader
        eyebrow="ABOUT & ETHICS"
        title="An assistant to your judgment."
        description="Nigehbaan means guardian. Our purpose is to help you spot warning signs before you act."
      />
      <div className="two-columns">
        <section className="panel">
          <h2>How it works</h2>
          <ol className="steps">
            <li>
              <strong>Read the signal</strong>
              <p>
                Text preprocessing handles Roman Urdu spelling variation and
                common entities.
              </p>
            </li>
            <li>
              <strong>Combine the evidence</strong>
              <p>
                A trained LR/SVM ensemble, expert rules and a separate static
                URL model contribute to the assessment.
              </p>
            </li>
            <li>
              <strong>Explain the warning</strong>
              <p>
                Risk levels and rule descriptions help you review a request. The
                system never blocks or deletes messages.
              </p>
            </li>
          </ol>
        </section>
        <section className="panel">
          <h2>What the numbers mean</h2>
          <p className="muted">
            Model Lab shows validation results, not final test results. The
            custom text data remains human-unverified. URL scores are
            source-specific and known false positives exist.
          </p>
          <p className="muted">
            Sarcasm, unfamiliar spellings, context and new scams can be missed.
            A low score does not establish safety, and a high score does not
            prove wrongdoing.
          </p>
          <div className="notice">
            Check urgent money or credential requests through an independently
            trusted contact.
          </div>
        </section>
      </div>
      <section className="panel mt">
        <h2>Your content stays yours.</h2>
        <p className="muted">
          No message text, transcripts, media, phone numbers or input URLs are
          stored. URL analysis does not visit links. Only high-risk result
          metadata is recorded locally. WhatsApp is not connected; no guardian
          messages are sent.
        </p>
      </section>
    </>
  );
}
