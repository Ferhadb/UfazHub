export default function Home() {
  return (
    <main id="main" className="relative z-10 mx-auto max-w-5xl px-4 py-12 sm:px-8 sm:py-24">
      <p className="text-step--1 text-muted font-mono tracking-widest uppercase">
        UFAZ Hub · Baku &amp; Paris
      </p>
      <h1 className="font-display text-step-5 text-ink mt-4 max-w-3xl">
        The library <em className="text-accent">we wrote</em> ourselves.
      </h1>
      <p className="text-step-1 text-muted mt-6 max-w-xl">
        Resources, articles and answers from UFAZ students. The shelves are being built; come back
        soon.
      </p>

      <article
        aria-label="Sample catalogue card"
        className="border-t-resource bg-card shadow-paper relative mt-16 max-w-md -rotate-1 rounded-md border-t-4 p-6 transition-transform duration-(--duration-base) ease-out hover:rotate-0"
      >
        <p className="text-step--1 text-resource font-mono tracking-widest uppercase">RES-0000</p>
        <h2 lang="az" className="text-step-2 text-ink mt-2">
          Əlgəbr və həndəsə: Iı İi Şş Çç Ğğ Öö Üü
        </h2>
        <p lang="fr" className="text-step-0 text-muted mt-3">
          À lire avant l’examen : é è ê à ç œ « très utile ».
        </p>
        <p lang="ru" className="text-step-0 text-muted mt-1">
          Ёё Щщ Ыы: читать перед экзаменом.
        </p>
        <span className="border-flame-text text-step--1 text-flame-text absolute -top-3 right-4 rotate-3 rounded-sm border-2 px-2 py-0.5 font-mono tracking-widest uppercase">
          New
        </span>
      </article>
    </main>
  );
}
