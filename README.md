# Sito di Di Lazzaro, fisioterapista e osteopata

Sito di una pagina per presentare il fisioterapista e osteopata Di Lazzaro (Roma, centro Fisiotorrino, via di Fiume Bianco 56, tel. 06 5201799).
Solo file statici, nessun servizio esterno (i caratteri sono nella cartella `public/fonts`), tema chiaro e scuro che segue il sistema.

```
public/index.html     la pagina (testi, struttura, dati per Google)
public/style.css      stile e colori (in cima ci sono i colori dei due temi)
public/foto.jpg       ritratto (foto-640.jpg è la versione per telefoni)
public/fonts/         Lora e Instrument Sans (licenza OFL)
scripts/make-artifact.mjs   crea dist/anteprima.html, la pagina in un solo file da mandare a chi non ha il sito online
wrangler.jsonc        pubblicazione su Cloudflare
```

## Da completare prima di andare online

- Nome e cognome per esteso del professionista (ora c'è solo «Di Lazzaro», letto sul camice della foto).
- Dati obbligatori nel piè di pagina (partita IVA, iscrizione all'albo professionale) e informativa privacy.
- Orari e giorni di visita, se il centro vuole mostrarli.
- Altre foto (studio, trattamenti) e una foto per la condivisione sui social.
- Togliere `noindex` da `public/index.html` e cancellare `public/robots.txt` quando il sito va sul dominio vero, altrimenti non comparirà su Google.
- Recensioni: la sezione «Cosa dicono i pazienti» ora ha solo il collegamento alla scheda Google. Per mostrare le recensioni vere si copiano da Google (testo, stelle, nome e iniziale, mese) e si inseriscono in `public/index.html`, dove c'è il blocco di esempio commentato. Mai inventarle.
- Controllare con lui l'elenco dei motivi di visita nella sezione «Di che cosa mi occupo».

## Pubblicare su Cloudflare

1. Workers & Pages, Create, Import a repository, scegli questo repo (ramo `main`).
2. Nome del progetto `dilazzaro-fisio`, Build command vuoto, Deploy command `npx wrangler deploy`.
3. L'indirizzo provvisorio sarà `https://dilazzaro-fisio.<tuo-account>.workers.dev`. Dominio vero: Settings, Domains & Routes.
