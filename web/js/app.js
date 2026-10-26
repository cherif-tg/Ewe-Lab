/* Interface du dictionnaire français–éwé : routeur par ancre, recherche, fiche,
   signalement. Aucune dépendance, aucun build : le fichier est servi tel quel. */

const base = (document.querySelector('meta[name="api-base"]')?.content || "").replace(/\/+$/, "");

const vue = document.getElementById("vue");
const champ = document.getElementById("champ");
const formRecherche = document.getElementById("form-recherche");
const boutonEffacer = document.getElementById("effacer");
const annonce = document.getElementById("annonce");
const boutonMaj = document.getElementById("maj");
const barre = document.querySelector(".barre-caracteres");

let majuscules = false;
let jeton = 0;            // invalide les réponses arrivées trop tard
let controleur = null;    // annule la requête précédente
let cacheJour = null;
let cacheStats = null;

/* ------------------------------------------------------------------ */
/* Utilitaires                                                         */
/* ------------------------------------------------------------------ */
const echappe = (valeur) =>
  String(valeur ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));

async function appel(chemin, options = {}) {
  const reponse = await fetch(base + chemin, {
    ...options,
    headers: { Accept: "application/json", ...(options.headers || {}) },
  });
  if (!reponse.ok) {
    let detail = `erreur ${reponse.status}`;
    try {
      const corps = await reponse.json();
      if (typeof corps.detail === "string") detail = corps.detail;
    } catch { /* corps non JSON */ }
    const erreur = new Error(detail);
    erreur.statut = reponse.status;
    throw erreur;
  }
  return reponse.json();
}

function messageErreur(erreur) {
  if (erreur.name === "AbortError") return "";
  const introuvable = erreur.statut === 404;
  const texte = introuvable
    ? "Ce mot n'est pas dans le dictionnaire."
    : `Le service ne répond pas (${echappe(erreur.message)}).`;
  return `<p class="erreur" role="alert">${texte}
    ${introuvable ? '<a href="#/">Revenir à l\'accueil</a>' : '<button class="bouton" type="button" data-reessayer>Réessayer</button>'}
  </p>`;
}

function annoncer(texte) {
  annonce.textContent = "";
  window.setTimeout(() => { annonce.textContent = texte; }, 30);
}

function focusTitre() {
  const titre = document.querySelector("#heros:not([hidden]) h1") || vue.querySelector("h1");
  if (!titre) return;
  titre.setAttribute("tabindex", "-1");
  titre.focus({ preventScroll: true });
}

/* ------------------------------------------------------------------ */
/* Vues                                                                */
/* ------------------------------------------------------------------ */
function carteJour(fiche) {
  const principal = fiche.sens.find((s) => s.type === "principal") || fiche.sens[0];
  const premiere = principal?.traductions?.[0] ?? "";
  return `<section class="carte-jour" aria-labelledby="titre-jour">
    <h2 id="titre-jour">Mot du jour</h2>
    <a href="#/mot/${fiche.id}">
      <p class="mot">${echappe(fiche.mot)}</p>
      <p class="traduction" lang="ee">${echappe(premiere)}</p>
    </a>
  </section>`;
}

/* ------------------------------------------------------------------ */
/* Contenus éditoriaux                                                 */
/* ------------------------------------------------------------------ */
const NOM = "Agbalẽ";
const TITRE_BASE = `${NOM} — dictionnaire français–éwé`;

const ETAPES = [
  ["Cherche un mot", "Français d'abord. Les fautes de frappe sont rattrapées : « abaissment » propose « abaissement »."],
  ["Lis la fiche", "Sens principal, expressions et précisions de sens. Chaque fiche garde la graphie numérisée d'origine."],
  ["Corrige", "Un bouton Signaler sur chaque fiche. Les corrections sont relues avant d'entrer dans la base."],
];

const FAQ = [
  {
    question: "D'où viennent les données ?",
    reponse: "D'un dictionnaire français–éwé numérisé, converti en base interrogeable. L'identification précise de l'édition et la vérification des droits sont en cours : d'ici là, la consultation est ouverte mais la base n'est pas téléchargeable.",
  },
  {
    question: "Pourquoi certaines traductions semblent-elles fausses ?",
    reponse: "La numérisation a introduit des erreurs systématiques : lettres éwés remplacées par des accents (<span lang=\"ee\">î</span> pour <span lang=\"ee\">ƒ</span>, <span lang=\"ee\">ô</span> pour <span lang=\"ee\">ɔ</span>), mots collés, restes de notes de bas de page. Les règles de correction sont versionnées et ne s'appliquent qu'après validation ; le taux d'erreur estimé sera publié après relecture d'un échantillon de 200 sens.",
  },
  {
    question: "Que montre le bouton « Texte d'origine » ?",
    reponse: "Chaque terme affiché est une forme corrigée. Ce bouton révèle la graphie telle qu'elle a été numérisée, sans retouche — utile pour juger une correction ou signaler une erreur.",
  },
  {
    question: "Pourquoi voit-on encore ê, ë, ï ou û ?",
    reponse: "Ce sont des graphies d'origine en attente de validation. Les règles sûres (<span lang=\"ee\">ƒ</span>, <span lang=\"ee\">ɔ</span>, <span lang=\"ee\">ã</span>) sont déjà appliquées ; les autres attendent une relecture par un locuteur natif, parce qu'une conversion hâtive produirait des mots faux : <span lang=\"ee\">agbalẽ</span> (« livre ») ne s'écrit pas <span lang=\"ee\">agbalê</span>.",
  },
  {
    question: "Les mots proposés sont-ils encore utilisés ?",
    reponse: "Le lexique source est ancien : certains termes ont vieilli ou changé de sens. Le bouton Signaler permet justement de répondre à « ce mot est-il encore utilisé aujourd'hui ? ».",
  },
  {
    question: "Comment signaler une erreur ou proposer une traduction ?",
    reponse: "Sur chaque fiche, bouton Signaler : type de retour, message, contact facultatif. Les signalements sont relus avant d'entrer dans la base ; aucun n'est appliqué automatiquement.",
  },
  {
    question: "Est-ce gratuit ? Faut-il un compte ?",
    reponse: "Gratuit, sans compte, sans publicité et sans traceur. Le contact d'un signalement est facultatif et n'est jamais publié tel quel.",
  },
  {
    question: "Peut-on télécharger la base ou l'utiliser ailleurs ?",
    reponse: "Pas encore. Tant que les droits du lexique source ne sont pas établis, seul l'accès par la recherche est proposé ; aucun export n'est distribué.",
  },
  {
    question: "Existe-t-il l'éwé vers le français ?",
    reponse: "Pas dans cette version : la recherche va du français vers l'éwé. La base est déjà indexée dans les deux sens, la recherche inverse est prévue.",
  },
  {
    question: "Y a-t-il de l'audio ou la prononciation ?",
    reponse: "Pas en v1. Des enregistrements de locuteurs natifs, avec consentement écrit, sont envisagés pour la suite.",
  },
  {
    question: "Comment écrire ɛ, ɔ, ɖ depuis mon téléphone ?",
    reponse: "La barre de caractères sous le champ de recherche insère les sept lettres éwés ; un appui long insère la majuscule. Les touches font 44 px pour rester utilisables au pouce.",
  },
  {
    question: "Et l'accessibilité ?",
    reponse: 'Contrastes conformes au seuil AA, zones tactiles de 44 px, navigation clavier avec focus visible, textes éwés balisés <code>lang="ee"</code> pour les lecteurs d\'écran, et mode sombre automatique selon le système.',
  },
];

function blocEtapes() {
  return `<section aria-labelledby="titre-etapes">
    <h2 id="titre-etapes">Comment ça marche</h2>
    <ol class="etapes">${ETAPES.map(
      ([titre, texte], index) => `<li>
        <span class="etape-num" aria-hidden="true">${index + 1}</span>
        <div><h3>${titre}</h3><p>${texte}</p></div>
      </li>`,
    ).join("")}</ol>
  </section>`;
}

function blocFaq(items, avecLien = false) {
  return `<section class="bloc-faq" aria-labelledby="titre-faq">
    <h2 id="titre-faq">Questions fréquentes</h2>
    <div class="faq">${items
      .map((item) => `<details><summary>${item.question}</summary><p>${item.reponse}</p></details>`)
      .join("")}</div>
    ${avecLien ? '<p class="faq-lien"><a href="#/faq">Toutes les questions</a></p>' : ""}
  </section>`;
}

async function chiffresHeros() {
  const cible = document.getElementById("heros-chiffres");
  if (!cible) return;
  try {
    cacheStats = cacheStats || (await appel("/v1/stats"));
    cible.textContent = `${cacheStats.entrees.toLocaleString("fr-FR")} entrées · ${cacheStats.traductions.toLocaleString("fr-FR")} traductions · français → éwé`;
    cible.hidden = false;
  } catch { /* les chiffres ne sont pas essentiels */ }
}

async function vueAccueil() {
  document.title = TITRE_BASE;
  vue.innerHTML = `
    <div id="jour"><p class="chargement">Mot du jour…</p></div>
    ${blocEtapes()}
    ${blocFaq(FAQ.slice(0, 3), true)}`;
  chiffresHeros();
  try {
    cacheJour = cacheJour || (await appel("/v1/word-of-the-day"));
    const cible = document.getElementById("jour");
    if (cible) cible.innerHTML = carteJour(cacheJour);
  } catch (erreur) {
    const cible = document.getElementById("jour");
    if (cible) cible.innerHTML = messageErreur(erreur);
  }
}

function vueFaq() {
  document.title = `Questions fréquentes — ${NOM}`;
  vue.innerHTML = `
    <h1>Questions fréquentes</h1>
    <p class="intro">Ce qui fonctionne, ce qui reste fragile, et pourquoi.</p>
    <div class="faq">${FAQ.map(
      (item) => `<details><summary>${item.question}</summary><p>${item.reponse}</p></details>`,
    ).join("")}</div>
    <p class="transparence">Une erreur à signaler, une traduction à proposer ?
      <button type="button" class="lien" data-action="signaler-general">Écrivez-nous</button>.</p>`;
}

function ligneResultat(r) {
  const nature = r.nature ? `<span class="nature">${echappe(r.nature)}</span>` : "";
  const traduction = r.premiere_traduction
    ? `<span class="trad" lang="ee">${echappe(r.premiere_traduction)}</span>`
    : "";
  return `<li><a href="#/mot/${r.id}">
    <span class="mot">${echappe(r.mot)}</span>${nature}${traduction}
  </a></li>`;
}

function rendreResultats(q, donnees) {
  const suggestions = donnees.suggestions.length
    ? `<div class="vouliez">
        <p>Vouliez-vous dire ?</p>
        <ul>${donnees.suggestions
          .map((s) => `<li><button type="button" data-suggestion="${echappe(s)}" lang="ee">${echappe(s)}</button></li>`)
          .join("")}</ul>
      </div>`
    : "";
  const liste = donnees.results.length
    ? `<ul class="resultats">${donnees.results.map(ligneResultat).join("")}</ul>`
    : `<p class="message-vide">Aucun mot trouvé pour « ${echappe(q)} ».</p>`;
  const resume = donnees.results.length
    ? `<p class="resume">${donnees.count} résultat${donnees.count > 1 ? "s" : ""} pour « ${echappe(q)} »</p>`
    : "";
  return `<section aria-labelledby="titre-resultats">
    <h1 id="titre-resultats" class="sr-only">Résultats de recherche</h1>
    ${suggestions}${resume}${liste}
  </section>`;
}

async function vueRecherche(q) {
  document.title = `${q} — ${NOM}`;
  if (champ.value !== q) champ.value = q;
  boutonEffacer.hidden = !q;
  const numero = ++jeton;
  if (controleur) controleur.abort();
  controleur = new AbortController();
  vue.innerHTML = `<p class="chargement">Recherche…</p>`;
  try {
    const donnees = await appel(`/v1/search?q=${encodeURIComponent(q)}&limit=30`, { signal: controleur.signal });
    if (numero !== jeton) return;
    vue.innerHTML = rendreResultats(q, donnees);
    annoncer(`${donnees.count} résultat${donnees.count > 1 ? "s" : ""} pour ${q}`);
  } catch (erreur) {
    if (numero !== jeton || erreur.name === "AbortError") return;
    vue.innerHTML = messageErreur(erreur);
  }
}

function rendreFiche(f) {
  const groupes = [
    ["principal", "Sens principal"],
    ["collocation", "Expressions"],
    ["glose", "Précisions de sens"],
  ];
  const sections = groupes
    .map(([type, titre]) => {
      const sens = f.sens.filter((s) => s.type === type);
      if (!sens.length) return "";
      const blocs = sens
        .map((s) => {
          const termes = s.traductions
            .map((t, i) => {
              const brut = s.bruts?.[i];
              const original = brut && brut !== t ? `<span class="brut" lang="ee">${echappe(brut)}</span>` : "";
              return `<span class="terme" lang="ee">${echappe(t)}</span>${original}`;
            })
            .join("");
          const repere = type === "collocation"
            ? `<div class="expression">${echappe(s.phrase)}</div>`
            : type === "glose" && s.libelle
              ? `<div class="expression">${echappe(s.libelle)}</div>`
              : "";
          return `<div class="sens">${repere}<p class="traductions">${termes}</p></div>`;
        })
        .join("");
      return `<section class="groupe"><h2>${titre}</h2>${blocs}</section>`;
    })
    .join("");

  const nature = f.nature ? `<span class="nature">${echappe(f.nature)}</span>` : "";
  const icone = (chemin) =>
    `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75"
      stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${chemin}"></path></svg>`;

  return `
    <article class="fiche">
      <header class="fiche-entete">
        <h1>${echappe(f.mot)}</h1>
        ${nature}
      </header>
      ${sections}
      <div class="actions">
        <button class="bouton" type="button" data-action="copier">
          ${icone("M9 9h10v10H9zM5 15V5h10")}Copier
        </button>
        <button class="bouton" type="button" data-action="partager">
          ${icone("M12 16V4m0 0L8 8m4-4l4 4M5 16v3a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3")}Partager
        </button>
        <button class="bouton" type="button" data-action="signaler">
          ${icone("M5 21V4m0 0h9l-1.5 3L14 10H5")}Signaler
        </button>
        <button class="bouton" type="button" data-action="brut" aria-pressed="false">
          ${icone("M4 7h16M4 12h16M4 17h10")}Texte d'origine
        </button>
      </div>
      <p class="transparence">
        Données issues d'un lexique numérisé : des erreurs de transcription sont possibles.
        <a href="#/a-propos">En savoir plus</a> ou signalez-la avec le bouton ci-dessus.
      </p>
    </article>`;
}

async function vueMot(id) {
  champ.value = "";
  boutonEffacer.hidden = true;
  const numero = ++jeton;
  vue.innerHTML = `<p class="chargement">Chargement…</p>`;
  try {
    const fiche = await appel(`/v1/entry/${id}?brut=true`);
    if (numero !== jeton) return;
    vue.innerHTML = rendreFiche(fiche);
    document.title = `${fiche.mot} — ${NOM}`;
    vue.dataset.mot = fiche.mot;
    vue.dataset.id = String(fiche.id);
    annoncer(`Fiche de ${fiche.mot}`);
  } catch (erreur) {
    if (numero !== jeton) return;
    vue.innerHTML = messageErreur(erreur);
  }
}

function vueApprendre() {
  document.title = `Apprendre l'éwé — ${NOM}`;
  const lecons = [
    ["L'alphabet éwé", "Lettres spéciales, digraphes, majuscules"],
    ["Écrire l'éwé", "Saisir les bons caractères, distinguer d et ɖ"],
    ["Lire l'éwé", "Syllabes, mots simples, repères de prononciation"],
    ["Les tons", "Sensibilisation : l'éwé est une langue tonale"],
    ["Vocabulaire par thèmes", "Salutations, nombres, famille, marché"],
  ];
  vue.innerHTML = `
    <h1>Apprendre l'éwé</h1>
    <p class="intro">Le mini-parcours arrive après la première version du dictionnaire.
      Chaque leçon sera relue par un locuteur natif avant publication ; aucune ne sera
      publiée à l'état de brouillon.</p>
    <ul class="resultats">
      ${lecons.map(([titre, resume]) => `<li><a href="#/apprendre">
        <span class="mot">${titre}</span><span class="nature">à venir</span>
        <span class="trad">${resume}</span></a></li>`).join("")}
    </ul>`;
}

async function vueAPropos() {
  document.title = `À propos — ${NOM}`;
  vue.innerHTML = `
    <h1>À propos</h1>
    <p class="intro">Un dictionnaire de consultation, français vers éwé, construit sur un
      lexique numérisé. La recherche est instantanée, la fiche d'un mot regroupe son sens
      principal, ses expressions et ses précisions de sens.</p>
    <div id="chiffres"><p class="chargement">Chiffres…</p></div>
    <h2>Sources et droits</h2>
    <p>Le texte de départ est un dictionnaire français–éwé numérisé. L'identification précise
      de l'édition et la vérification des droits sont en cours : tant qu'elles ne sont pas
      établies, seule la consultation est proposée, sans téléchargement de la base.</p>
    <h2>Qualité des données</h2>
    <p>La numérisation a introduit des erreurs de transcription : caractères éwés remplacés,
      mots scindés, restes de notes de bas de page. Les graphies d'origine sont conservées et
      consultables depuis chaque fiche. Le taux d'erreur estimé sera publié après
      l'échantillonnage de 200 sens prévu par l'étude de cadrage.</p>
    <p class="transparence">Données issues d'un lexique numérisé. Des erreurs de transcription
      sont possibles. Certains termes peuvent être anciens. Vos signalements servent à corriger
      la base.</p>`;

  try {
    const s = await appel("/v1/stats");
    const cible = document.getElementById("chiffres");
    if (!cible) return;
    cible.innerHTML = `<dl class="chiffres">
      <div><dt>Entrées</dt><dd>${s.entrees.toLocaleString("fr-FR")}</dd></div>
      <div><dt>Traductions</dt><dd>${s.traductions.toLocaleString("fr-FR")}</dd></div>
      <div><dt>Version des données</dt><dd>${echappe(s.version_donnees ?? "—")}</dd></div>
      <div><dt>Taux d'erreur estimé</dt><dd>${s.taux_erreur_estime == null ? "en cours de mesure" : `${s.taux_erreur_estime} %`}</dd></div>
    </dl>`;
  } catch (erreur) {
    const cible = document.getElementById("chiffres");
    if (cible && erreur.name !== "AbortError") cible.innerHTML = messageErreur(erreur);
  }
}

/* ------------------------------------------------------------------ */
/* Routeur                                                             */
/* ------------------------------------------------------------------ */
const routes = [
  { motif: /^\/?$/, vue: vueAccueil, nav: "dictionnaire" },
  { motif: /^\/recherche\/(.+)$/, vue: (m) => vueRecherche(decodeURIComponent(m[1])), nav: "dictionnaire" },
  { motif: /^\/mot\/(\d+)$/, vue: (m) => vueMot(Number(m[1])), nav: "dictionnaire" },
  { motif: /^\/faq\/?$/, vue: vueFaq, nav: "" },
  { motif: /^\/apprendre\/?$/, vue: vueApprendre, nav: "apprendre" },
  { motif: /^\/a-propos\/?$/, vue: vueAPropos, nav: "a-propos" },
];

function majNavigation(nav) {
  document.querySelectorAll("[data-nav]").forEach((lien) => {
    if (lien.dataset.nav === nav) lien.setAttribute("aria-current", "page");
    else lien.removeAttribute("aria-current");
  });
}

async function rendre({ focus = false } = {}) {
  const chemin = (location.hash.replace(/^#/, "") || "/").replace(/\/+$/, "") || "/";
  const route = routes.find((r) => r.motif.test(chemin)) || routes[0];
  const correspondance = chemin.match(route.motif) || [];
  majNavigation(route.nav);
  const accueil = chemin === "/";
  document.getElementById("heros").hidden = !accueil;
  document.getElementById("exemples").hidden = !accueil;
  await route.vue(correspondance);
  if (focus) focusTitre();
}

function remplacerAdresse(hash) {
  if (location.hash !== hash) history.replaceState(null, "", hash);
}

function pousserAdresse(hash) {
  if (location.hash !== hash) history.pushState(null, "", hash);
}

/* ------------------------------------------------------------------ */
/* Recherche                                                           */
/* ------------------------------------------------------------------ */
let minuteur;

champ.addEventListener("input", () => {
  const q = champ.value.trim();
  boutonEffacer.hidden = !champ.value;
  clearTimeout(minuteur);
  minuteur = window.setTimeout(() => {
    if (!q) {
      remplacerAdresse("#/");
      rendre();
      return;
    }
    remplacerAdresse(`#/recherche/${encodeURIComponent(q)}`);
    vueRecherche(q);
  }, 200);
});

formRecherche.addEventListener("submit", (evenement) => {
  evenement.preventDefault();
  const q = champ.value.trim();
  if (!q) return;
  clearTimeout(minuteur);
  pousserAdresse(`#/recherche/${encodeURIComponent(q)}`);
  vueRecherche(q);
});

boutonEffacer.addEventListener("click", () => {
  champ.value = "";
  boutonEffacer.hidden = true;
  champ.focus();
  remplacerAdresse("#/");
  rendre();
});

window.addEventListener("hashchange", () => rendre({ focus: true }));

/* ------------------------------------------------------------------ */
/* Barre de caractères éwés                                            */
/* ------------------------------------------------------------------ */
function inserer(texte) {
  const debut = champ.selectionStart ?? champ.value.length;
  const fin = champ.selectionEnd ?? debut;
  champ.value = champ.value.slice(0, debut) + texte + champ.value.slice(fin);
  const position = debut + texte.length;
  champ.focus();
  champ.setSelectionRange(position, position);
  champ.dispatchEvent(new Event("input", { bubbles: true }));
}

boutonMaj.addEventListener("click", () => {
  majuscules = !majuscules;
  boutonMaj.setAttribute("aria-pressed", String(majuscules));
});

let minuteurAppui = null;
let appuiLong = false;

barre.addEventListener("pointerdown", (evenement) => {
  const touche = evenement.target.closest("[data-caractere]");
  if (!touche) return;
  appuiLong = false;
  minuteurAppui = window.setTimeout(() => {
    appuiLong = true;
    inserer(touche.dataset.caractere.toLocaleUpperCase("fr"));
  }, 450);
});

["pointerup", "pointercancel"].forEach((type) =>
  barre.addEventListener(type, () => clearTimeout(minuteurAppui)),
);

barre.addEventListener("click", (evenement) => {
  const touche = evenement.target.closest("[data-caractere]");
  if (!touche) return;
  if (appuiLong) { appuiLong = false; return; }
  const caractere = majuscules ? touche.dataset.caractere.toLocaleUpperCase("fr") : touche.dataset.caractere;
  inserer(caractere);
});

/* ------------------------------------------------------------------ */
/* Actions de la fiche                                                 */
/* ------------------------------------------------------------------ */
function texteACopier() {
  const mot = vue.dataset.mot || "";
  const lignes = [];
  vue.querySelectorAll(".groupe").forEach((groupe) => {
    groupe.querySelectorAll(".sens").forEach((sens) => {
      const repere = sens.querySelector(".expression")?.textContent?.trim();
      const termes = [...sens.querySelectorAll(".terme")].map((t) => t.textContent.trim()).join(", ");
      if (!termes) return;
      lignes.push(repere ? `${repere} : ${termes}` : termes);
    });
  });
  return [mot, ...lignes].filter(Boolean).join("\n");
}

async function copier(texte) {
  try {
    await navigator.clipboard.writeText(texte);
    annoncer("Copié dans le presse-papiers.");
  } catch {
    annoncer("La copie automatique n'est pas disponible sur cet appareil.");
  }
}

vue.addEventListener("click", async (evenement) => {
  const suggestion = evenement.target.closest("[data-suggestion]");
  if (suggestion) {
    const mot = suggestion.dataset.suggestion;
    champ.value = mot;
    boutonEffacer.hidden = false;
    pousserAdresse(`#/recherche/${encodeURIComponent(mot)}`);
    vueRecherche(mot);
    champ.focus();
    return;
  }

  if (evenement.target.closest("[data-reessayer]")) {
    rendre();
    return;
  }

  const action = evenement.target.closest("[data-action]")?.dataset.action;
  if (!action) return;

  if (action === "copier") {
    await copier(texteACopier());
  } else if (action === "partager") {
    const url = `${location.origin}${location.pathname}#/mot/${vue.dataset.id}`;
    const titre = `${vue.dataset.mot} — ${NOM}, dictionnaire français–éwé`;
    if (navigator.share) {
      try { await navigator.share({ title: titre, url }); } catch { /* partage annulé */ }
    } else {
      await copier(url);
    }
  } else if (action === "signaler") {
    ouvrirSignalement(Number(vue.dataset.id), vue.dataset.mot);
  } else if (action === "signaler-general") {
    ouvrirSignalement(null, null);
  } else if (action === "brut") {
    const actif = document.body.classList.toggle("afficher-brut");
    evenement.target.closest("[data-action]").setAttribute("aria-pressed", String(actif));
  }
});

/* ------------------------------------------------------------------ */
/* Signalement                                                         */
/* ------------------------------------------------------------------ */
const dialogue = document.getElementById("dialogue-signalement");
const formSignalement = document.getElementById("form-signalement");
const messageSignalement = document.getElementById("message-signalement");
let entreeSignalee = null;

function ouvrirSignalement(id, mot) {
  entreeSignalee = Number.isFinite(id) ? id : null;
  formSignalement.reset();
  messageSignalement.textContent = "";
  messageSignalement.className = "message";
  document.getElementById("contexte-signalement").textContent = mot ? `À propos de « ${mot} »` : "";
  dialogue.showModal();
}

document.getElementById("annuler-signalement").addEventListener("click", () => dialogue.close());

formSignalement.addEventListener("submit", async (evenement) => {
  evenement.preventDefault();
  const donnees = new FormData(formSignalement);
  const corps = {
    entree_id: entreeSignalee,
    type: donnees.get("type"),
    texte: String(donnees.get("texte") || "").trim(),
    contact: String(donnees.get("contact") || "").trim() || null,
  };
  messageSignalement.className = "message";
  messageSignalement.textContent = "Envoi…";
  try {
    const reponse = await fetch(`${base}/v1/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corps),
    });
    if (reponse.status === 201) {
      messageSignalement.className = "message ok";
      messageSignalement.textContent = "Merci, votre message est enregistré.";
      window.setTimeout(() => dialogue.close(), 1200);
    } else if (reponse.status === 429) {
      messageSignalement.className = "message ko";
      messageSignalement.textContent = "Trop de signalements envoyés. Réessayez dans quelques minutes.";
    } else {
      const corpsErreur = await reponse.json().catch(() => ({}));
      messageSignalement.className = "message ko";
      messageSignalement.textContent =
        typeof corpsErreur.detail === "string" ? corpsErreur.detail : "Le message n'a pas pu être enregistré.";
    }
  } catch {
    messageSignalement.className = "message ko";
    messageSignalement.textContent = "Le service ne répond pas.";
  }
});

/* ------------------------------------------------------------------ */
/* Démarrage                                                           */
/* ------------------------------------------------------------------ */
document.getElementById("commencer").addEventListener("click", () => {
  const doux = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  formRecherche.scrollIntoView({ behavior: doux ? "smooth" : "auto", block: "center" });
  champ.focus({ preventScroll: true });
  annoncer("Champ de recherche prêt : tape un mot français.");
});

document.getElementById("exemples").addEventListener("click", (evenement) => {
  const bouton = evenement.target.closest("[data-exemple]");
  if (!bouton) return;
  const mot = bouton.dataset.exemple;
  champ.value = mot;
  boutonEffacer.hidden = false;
  pousserAdresse(`#/recherche/${encodeURIComponent(mot)}`);
  vueRecherche(mot);
});

document.getElementById("signaler-general").addEventListener("click", () => ouvrirSignalement(null, null));

rendre();
