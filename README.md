# Tractage Nanterre — où et quand tracter

Carte des lieux où tracter à Nanterre, **par boucle** et **par créneau horaire** : écoles
(entrée et sortie), marchés et leurs jours, gares aux heures de pointe, grandes surfaces
aux heures d'affluence, université et écoles supérieures, France Travail, parcs… plus un
agenda des événements ponctuels (fête de l'engagement, bords de Seine, fêtes de l'hiver,
Parade(s), animations de Noël des marchés).

Même principe que l'outil [Collage](https://github.com/ArmanAkg/collage-nanterre) : une page
statique, aucune installation, utilisable au téléphone.

## 👉 Ouvrir l'outil

**<https://armanakg.github.io/tractage-nanterre/>**

## Publier / mettre à jour le site

Comme Collage : page statique servie par **GitHub Pages** depuis la branche `main`
(Settings → Pages → Source : Deploy from a branch → `main` / `(root)`). Chaque `git push`
met le site à jour en une minute environ.

## Développer en local

```bash
python -m http.server 8778
```

puis <http://localhost:8778/outil-tractage.html>. Le double-clic ne marche pas : le
navigateur refuse de lire `lieux.json` en `file://`.

## Ce qu'on peut faire

- **Lieux** : tous les lieux sont affichés en permanence sur la carte, et listés par boucle
  avec le moment où y aller (« lun, mar, jeu, ven · 8h30–8h50, 16h20–16h45 »). La légende
  permet de masquer un type de lieu ; la recherche filtre par nom ou par rue.
- **Agenda** : les événements à venir, les vacances scolaires, et les rendez-vous annuels
  à guetter. Les événements des 60 prochains jours sont aussi posés sur la carte (pastille
  jaune, en arrière-plan : les lieux passent devant).
- **Boucles** : chaque boucle est une zone teintée ; son nom s'affiche au survol. Un clic sur
  la zone ou sur le titre dans la liste choisit la boucle : la carte zoome dessus, sa teinte
  s'ouvre pour laisser voir les rues et les autres boucles s'estompent. **Toute la ville**
  (en haut à droite), ou un clic hors de
  Nanterre, revient à la vue d'ensemble. Un lien du type
  `…/outil-tractage.html#PN` ouvre directement la carte sur une boucle : à épingler dans
  chaque groupe Telegram.
- Clic sur un lieu : tous ses créneaux, la note pratique, l'itinéraire à pied.
- Un bandeau signale les vacances scolaires en cours (écoles fermées).

## Les boucles

Les 6 boucles des bandeaux Telegram regroupent les 11 quartiers officiels (limites reprises
de `panneaux.json` de l'outil Collage) :

| Boucle | Quartiers |
|---|---|
| **CI** Chemin de l'Île | Chemin de l'Île |
| **UR** Université / République | Université, République |
| **CVP** Centre / Vieux-Pont | Centre, Vieux-Pont – Sainte-Geneviève |
| **PSN** Parc Sud / Parc Nord | Parc Sud, Parc Nord, **La Boule – Champs-Pierreux**, **Les Groues** |
| **MV** Mont-Valérien | Plateau – Mont-Valérien |
| **PN** Petit-Nanterre | Petit-Nanterre |

La Boule – Champs-Pierreux et Les Groues n'ont pas de bandeau à elles : elles sont
rattachées à PSN (choix validé le 29 octobre 2026). Pour changer un rattachement, modifier
`boucles` dans `lieux.json`, le champ `b` des lieux concernés, puis recalculer les zones
(voir plus bas).

Les zones dessinées sur la carte viennent de `zones.json` : les quartiers de chaque boucle
fusionnés en un seul contour, plus le contour de la ville. Les logos (`img/`) sont les
bandeaux Telegram de `../visus/logos_telegram/bandeau`, réduits à 128 px ; `img/logo.png`
(en-tête et icône d'onglet) est celui du pôle tractage. La couleur d'une
zone est le champ `c` de sa boucle : trois teintes des visuels Telegram, deux boucles voisines
n'ayant jamais la même.

## D'où viennent les données

Relevé du **29 octobre 2026** : 58 lieux, 10 événements. Le groupe a retenu 53 lieux et
10 événements sur une première liste de 119 lieux et 16 événements, puis ajouté 5 écoles
supérieures privées.

| Type | Source | Créneaux |
|---|---|---|
| Écoles (33) | annuaire Éducation nationale ; maternelle + élémentaire de même nom fusionnées en « groupe scolaire » | horaires de la ville (8h45–12h / 13h45–16h30, lun, mar, jeu, ven) : entrée 8h30–8h50, sortie 16h20–16h45 |
| Université (1) | OpenStreetMap | arrivées 8h–9h45, midi 11h45–14h, sorties 16h30–18h30 |
| Écoles supérieures privées (5) | effectifs étudiants du ministère, rentrée 2025 (`data.enseignementsup-recherche.gouv.fr`) : IÉSEG, pôle Léonard-de-Vinci (ESILV, EMLV), IIM, CESI, Ynov. L'École Conté, au bout de La Défense, est écartée | horaires types : arrivées 8h15–9h15, midi 12h–14h, sorties 17h–18h30 |
| Marchés (4 + 1) | jours : nanterre.fr ; heures : ot-nanterre.fr. Le Petit-Nanterre n'a pas de marché : celui des habitants est le **marché du Petit-Colombes** (485–497 rue Gabriel-Péri, Colombes ; mardi et vendredi 8h–12h45, dimanche 8h–13h30, colombes.fr), rattaché à PN | jours de marché, 9h–12h30 |
| Gares (4) | OpenStreetMap | lun–ven 7h–9h et 17h–19h30 |
| Grandes surfaces (4) | OpenStreetMap | **affluence estimée** (profil type), limitée aux heures d'ouverture OSM |
| France Travail (1), parcs (5) | OpenStreetMap | file du matin ; mercredi et week-end après-midi |
| Vacances scolaires | calendrier officiel (zone C, académie de Versailles) | |
| Événements | nanterre.fr (agenda, fiches marchés, magazine), sites associatifs | |

**Écartés lors de la sélection** (listés dans `outils/construire_lieux.py`, `CATS_RETIREES`
et `SUPERS_GARDES`) : lycées, collèges, centres sociaux, stades, hôpital, lieux culturels,
les services publics autres que France Travail, les supérettes et 7 des 11 grandes surfaces,
ainsi que les événements Rolex Paris Masters, mimosa, fête des mères et Octobre Rose aux
marchés, fête du commerce du Petit-Nanterre et rentrée scolaire. Les identifiants des lieux
gardés n'ont pas changé, d'où les trous dans la numérotation (S1, S6, S7, S23…).

**À vérifier sur le terrain, par ordre d'importance :**

1. **Affluence des grandes surfaces** — profil type (soirs de semaine, samedi), pas une
   mesure. À corriger avec les « heures d'affluence » de Google Maps magasin par magasin.
2. **Dates 2026-2027 des fêtes** — seules les animations de Noël des marchés (11–13 déc.)
   sont publiées. Les fêtes de l'hiver sont estimées d'après les éditions précédentes et
   marquées « à confirmer ».
3. **Écoles privées** (21, Sainte-Geneviève, Ibn Badis, Louqman) : horaires de la ville
   appliqués par défaut.
4. Les adresses précédées de `≈` sont l'adresse la plus proche du point, pas l'adresse
   officielle du lieu.

Les **lieux de culte** ne sont volontairement pas inclus.

## Modifier les données

`lieux.json` est la référence. Il est écrit **un lieu par ligne**, pour que `git diff` montre
exactement ce qui change. Un lieu :

```json
{"id": "M2", "cat": "marche", "nom": "Marché du Centre", "a": "Place du Maréchal Foch",
 "lat": 48.889315, "lon": 2.195269, "q": "Centre", "b": "CVP",
 "cr": [{"j": [2, 4, 7], "d": "09:00", "f": "12:30", "l": "marché (pic 10h–12h)", "p": 3}],
 "note": "…", "src": "nanterre.fr / ot-nanterre.fr"}
```

- `cr` : les créneaux. `j` = jours (1 = lundi … 7 = dimanche), `d`/`f` = début/fin,
  `l` = libellé, `p` = intérêt de 1 à 3. La liste n'affiche que les créneaux d'intérêt 2 ou
  3 ; la fiche du lieu les montre tous.
- `aff` : fréquentation estimée, en personnes par créneau (ordre de grandeur). Elle fixe la
  taille de la bulle, sur une échelle logarithmique : une gare (8 000) fait environ deux fois
  le diamètre d'une école (250). Valeurs de départ dans `AFFLUENCE` de
  `outils/construire_lieux.py` ; à corriger dans `lieux.json` après observation sur place.
- `aConfirmer: true` : marqueur en pointillés.
- Les catégories (`categories`) portent leur nom, leur couleur et leur icône
  [Tabler](https://tabler.io/icons) (`ic`, sans le préfixe `ti-`).
- Un événement : `d`/`f` (dates), `h` (heures, en texte), `statut` (`confirmé`,
  `à confirmer`, `passé`), `b` (boucle, ou `null` pour toute la ville), `refs` (lieux
  concernés) ou `lat`/`lon`, `periode` (quand il revient).

Quand une fête passe, mettre à jour sa date avec celle de l'édition suivante dès qu'elle est
annoncée, plutôt que d'ajouter une ligne.

## Régénérer depuis les sources

```bash
python outils/construire_lieux.py
```

⚠️ **Écrase `lieux.json`** et donc toutes les corrections faites à la main. À ne relancer que
pour repartir de zéro (nouvelle année scolaire, nouveaux supermarchés…), puis reporter les
corrections. La réponse OpenStreetMap est gardée dans `outils/cache_osm.json` : le supprimer
pour la rafraîchir. Les horaires des marchés, des écoles et les événements sont écrits dans le
script lui-même.

Pour recalculer `zones.json` (seulement si les boucles ou les quartiers changent) :

```bash
npm install @turf/turf@7          # une fois, dans un dossier de travail
NODE_PATH=<ce dossier>/node_modules node outils/zones_boucles.cjs
```

## Services externes

Fond de carte OpenStreetMap standard. Deux réglages en tête du script de la page permettent
de revenir aux variantes essayées : `FOND_DESATURE` (fond atténué par le filtre `.fond`) et
`LOGOS_SUR_CARTE` (logo Telegram au centre de chaque boucle, effacé quand on la choisit).
Icônes Tabler et police Public Sans chargées depuis jsDelivr et Google Fonts. Données
Éducation nationale (`data.education.gouv.fr`), Overpass et Base Adresse Nationale à la
construction seulement. Une connexion internet est nécessaire pour afficher la carte.
