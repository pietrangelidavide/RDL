# Instagram di Riccardo Di Lazzaro: pubblicazione automatica

Il calendario (`calendar.json`) contiene i post. Le immagini si generano dai modelli grafici
(`render.py`, stesso stile del sito). Un workflow GitHub controlla ogni 30 minuti se c'è un post
**approvato** la cui data è arrivata e lo pubblica con l'API ufficiale di Meta.

```
bozza (draft)  →  Riccardo legge e dice sì  →  approved + approved_by  →  alla data: published
```

Niente esce senza `status: "approved"` e `approved_by`. Il controllo di sicurezza (`publish.py lint`)
blocca anche didascalie con espressioni promozionali o comparative (sconto, garantito, il migliore,
prima e dopo…), la mancanza della frase «non sostituisce una visita» e le foto di pazienti senza
consenso scritto. È una rete di sicurezza, non una consulenza legale: la comunicazione sanitaria
resta sotto la responsabilità del professionista (L. 145/2018 e codice deontologico).

## Collegamento a Instagram (una volta sola)

1. **Account professionale.** Su Instagram: Impostazioni → Tipo di account e strumenti → passa a
   account professionale (Business o Creator).
2. **App Meta.** Su developers.facebook.com crea un'app (tipo Business), aggiungi il prodotto
   «Instagram» → «API con accesso Instagram». Resta in modalità sviluppo: basta per un account tuo.
3. **Tester.** Nei ruoli dell'app aggiungi l'account di Riccardo come «Tester Instagram»; Riccardo
   accetta l'invito da Instagram (Impostazioni → Siti web e app → Inviti tester).
4. **Token.** Nella configurazione API genera il token per l'account con i permessi
   `instagram_business_basic` e `instagram_business_content_publish`. Copia il token lungo e
   l'ID dell'account Instagram. (I nomi dei menu di Meta cambiano spesso.)
5. **Segreti GitHub.** Repo → Settings → Secrets and variables → Actions:
   - `IG_USER_ID`: ID dell'account Instagram
   - `IG_TOKEN`: il token
   - `GH_PAT` (facoltativo ma consigliato): token personale GitHub con «Secrets: read and write»
     solo su questa repo; serve a rinnovare in automatico `IG_TOKEN` ogni 60 giorni.
6. **Prova.** Actions → Instagram → Run workflow (con «dry run» attivo) per vedere cosa uscirebbe.

Le immagini sono servite da `raw.githubusercontent.com` (la repo deve essere pubblica). Con una repo
privata, o se Instagram rifiuta il video di un reel, imposta la variabile `MEDIA_BASE_URL` con un
altro indirizzo pubblico che serve la cartella `instagram/media`.

## Uso quotidiano

```bash
python3 instagram/render.py                 # genera immagini e video dei post non pubblicati
python3 instagram/publish.py lint           # controlla tutto
python3 instagram/publish.py status         # elenco dei post
python3 instagram/publish.py publish --dry-run --now 2026-11-04T18:30
python3 -m unittest discover -s instagram/tests   # prove con un server Meta finto
```

Per approvare un post: in `calendar.json` metti `"status": "approved"` e `"approved_by": "Riccardo Di Lazzaro"`,
poi `git push`. Alla data indicata (`publish_at`, ora di Roma) esce da solo. Se il workflow è fermo
per più di 36 ore, il post scaduto non viene pubblicato (si rimanda cambiando la data).

Tipi di post: `image`, `carousel` (2-10 slide), `reel` (campo `video`), `story`.
Modelli grafici: `cover`, `slide`, `mito`, `chiusura`, `quote`, `foto`, `passi` (vedi `templates.py`).
Instagram accetta solo JPEG per le immagini, per questo l'output è in `.jpg`.

## Cosa non è stato provato

Il flusso è provato contro un server finto che imita l'API (11 prove). Non è mai stata fatta una
pubblicazione reale: il primo post va controllato a mano.
