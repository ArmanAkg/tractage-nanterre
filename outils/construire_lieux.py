"""Construit lieux.json (carte de tractage Nanterre) a partir des sources ouvertes.

    python outils/construire_lieux.py

Sources : annuaire et calendrier scolaire de l'Education nationale (data.education.gouv.fr),
OpenStreetMap (Overpass), Base Adresse Nationale, limites de quartiers reprises de
../Collage/panneaux.json. Les horaires et evenements viennent de nanterre.fr et
ot-nanterre.fr (releves le 2026-10-29, voir README.md).

ATTENTION : relancer ce script ECRASE lieux.json. Une fois le fichier publie, c'est lui
qui fait foi : les corrections se font directement dans lieux.json (un lieu par ligne).
"""
import json, math, os, re, sys, unicodedata
from datetime import date, timedelta
import requests

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
COLLAGE = os.path.join(RACINE, '..', 'Collage', 'panneaux.json')
UA = {'User-Agent': 'tractage-nanterre/1.0 (usage militant local)', 'Accept': '*/*'}

# ---------------------------------------------------------------- boucles
# Les 6 boucles militantes (bandeaux Telegram) regroupent les 11 quartiers officiels.
# La Boule – Champs-Pierreux et Les Groues n'ont pas de boucle a elles : rattachees
# a la boucle la plus proche (Parc Sud / Parc Nord). A modifier ici ou dans lieux.json.
# c : teinte de la zone sur la carte, tiree des visuels Telegram ; deux boucles voisines
# n'ont jamais la meme teinte.
BOUCLES = [
    {'id': 'CI',  'nom': "Chemin de l'Île",        'c': '#d9c6f0', 'quartiers': ["Chemin de l'Île"]},
    {'id': 'UR',  'nom': 'Université / République', 'c': '#eadff7', 'quartiers': ['Université', 'République']},
    {'id': 'CVP', 'nom': 'Centre / Vieux-Pont',     'c': '#fbe3e1', 'quartiers': ['Centre', 'Vieux-Pont – Sainte-Geneviève']},
    {'id': 'PSN', 'nom': 'Parc Sud / Parc Nord',    'c': '#d9c6f0', 'quartiers': ['Parc Sud', 'Parc Nord', 'La Boule – Champs-Pierreux', 'Les Groues']},
    {'id': 'MV',  'nom': 'Mont-Valérien',           'c': '#eadff7', 'quartiers': ['Plateau – Mont-Valérien']},
    {'id': 'PN',  'nom': 'Petit-Nanterre',          'c': '#fbe3e1', 'quartiers': ['Petit-Nanterre']},
]
Q2B = {q: b['id'] for b in BOUCLES for q in b['quartiers']}

# ic : icone Tabler (https://tabler.io/icons) ; c : couleur du marqueur
CATEGORIES = {
    'ecole':   {'nom': 'Écoles',           'ic': 'school',             'c': '#4c0297'},
    'lycee':   {'nom': 'Lycées',           'ic': 'certificate',        'c': '#6d28d9'},
    'college': {'nom': 'Collèges',         'ic': 'books',              'c': '#6d28d9'},
    'univ':    {'nom': 'Université',       'ic': 'building-community', 'c': '#0b5cad'},
    'sup':     {'nom': 'Écoles supérieures', 'ic': 'certificate',      'c': '#b8327a'},
    'gare':    {'nom': 'Gares',            'ic': 'train',              'c': '#d1271c'},
    'marche':  {'nom': 'Marchés',          'ic': 'basket',             'c': '#0e8a4f'},
    'super':   {'nom': 'Grandes surfaces', 'ic': 'shopping-cart',      'c': '#e07b00'},
    'service': {'nom': 'France Travail',   'ic': 'briefcase',          'c': '#334155'},
    'social':  {'nom': 'Centres sociaux',  'ic': 'heart-handshake',    'c': '#be185d'},
    'parc':    {'nom': 'Parcs',            'ic': 'trees',              'c': '#2f9d8f'},
    'stade':   {'nom': 'Stades',           'ic': 'ball-football',      'c': '#0891b2'},
    'sante':   {'nom': 'Hôpital',          'ic': 'building-hospital',  'c': '#0f766e'},
    'culture': {'nom': 'Culture',          'ic': 'masks-theater',      'c': '#9333ea'},
}

# Selection faite par le groupe le 2026-10-29 sur la liste complete : ces categories sont
# ecartees, et seuls France Travail et 4 grandes surfaces sont gardes dans les leurs.
CATS_RETIREES = {'lycee', 'college', 'social', 'stade', 'sante', 'culture'}
SUPERS_GARDES = {('carrefour market', '33 boulevard du general leclerc'), ('intermarche', '7bis mail ambroise croizat'),
                 ('lidl', '461 boulevard des provinces francaises'), ('e leclerc nanterre', 'rue paul vaillant couturier')}

# Frequentation estimee (champ aff) : personnes qui passent pendant un creneau type, ordre de
# grandeur seulement. Elle fixe la taille du marqueur. Ecoles : 250 pour un groupe scolaire,
# 130 pour une maternelle seule, 100 pour une elementaire seule (parents a la grille).
# Gares : frequentation des heures de pointe (RER A tres charge) ; marches : selon le nombre
# de commercants publie par la ville.
# Ecoles superieures privees de Nanterre (effectifs etudiants du ministere, rentree 2025).
# ESILV et EMLV partagent le meme site, le pole Leonard-de-Vinci. Le CESI declare plus de
# 3 400 etudiants par an en comptant l'alternance et la formation continue.
# Lieux rattaches a la main a un autre quartier que celui de leur point : le parc du
# Chemin-de-l'Ile deborde sur Republique, mais c'est le parc du quartier du Chemin de l'Ile.
QUARTIER_FORCE = {'parc du chemin de l ile': "Chemin de l'Île"}

ECOLES_SUP = [
    ('IÉSEG School of Management (campus de Paris)', 48.89739, 2.22469, 6102, 'École de commerce.'),
    ('Pôle Léonard-de-Vinci (ESILV, EMLV)', 48.89646, 2.23633, 8902, 'École d’ingénieurs et école de management.'),
    ('IIM Digital School', 48.89496, 2.22634, 742, 'École du numérique (pôle Léonard-de-Vinci).'),
    ('CESI École d’ingénieurs (campus Paris-Nanterre)', 48.90347, 2.19329, 718, '93 boulevard de la Seine. Beaucoup d’alternants.'),
    ('Paris Ynov Campus', 48.90150, 2.20878, 699, 'Écoles du numérique, de l’audiovisuel et du design.'),
]

AFFLUENCE = {
    'gare nanterre prefecture': 8000, 'gare nanterre universite': 6000, 'gare nanterre ville': 3000,
    'gare nanterre la folie': 800,
    'marche du centre': 3000, 'marche de la gare': 2500, 'marche pablo picasso': 1200,
    'marche prefecture charles de gaulle': 800, 'marche du petit colombes': 1000,
    'e leclerc nanterre': 1500, 'lidl': 600, 'intermarche': 600, 'carrefour market': 500,
    'parc andre malraux': 1000, 'parc du chemin de l ile': 800, 'parc des anciennes mairies': 400,
}
AFFLUENCE_DEFAUT = {'univ': 5000, 'sup': 300, 'service': 150, 'parc': 200, 'super': 300, 'marche': 800}

LMJV, LV, SEM = [1, 2, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5, 6, 7]


def cr(j, d, f, l, p):
    """Creneau : jours (1 = lundi), debut, fin, libelle, interet 1 a 3."""
    return {'j': j, 'd': d, 'f': f, 'l': l, 'p': p}


# ---------------------------------------------------------------- outils
def norm(s):
    s = unicodedata.normalize('NFD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def metres(a, b, c, d):
    return math.hypot((a - c) * 111320, (b - d) * 111320 * math.cos(math.radians(a)))


def in_ring(lat, lon, r):
    c = False
    j = len(r) - 1
    for i in range(len(r)):
        y1, x1 = r[i]; y2, x2 = r[j]
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1 + 1e-15) + x1:
            c = not c
        j = i
    return c


def quartier(lat, lon, qs):
    for nom, rings in qs:
        if any(in_ring(lat, lon, r) for r in rings):
            return nom
    best, bd = None, 1e9                      # hors limites : quartier le plus proche
    for nom, rings in qs:
        for r in rings:
            for y, x in r:
                d = metres(lat, lon, y, x)
                if d < bd: bd, best = d, nom
    return best if bd < 800 else None


def ban(adresse, commune='92050'):
    r = requests.get('https://api-adresse.data.gouv.fr/search/', params={'q': adresse, 'citycode': commune, 'limit': 1},
                     headers=UA, timeout=30)
    f = r.json()['features'][0]
    lon, lat = f['geometry']['coordinates']
    return round(lat, 6), round(lon, 6), f['properties']['label'].replace(' 92000 Nanterre', '')


def hm(s):
    h, m = s.split(':'); return int(h) * 60 + int(m)


def fmt(mn):
    return '%02d:%02d' % (mn // 60, mn % 60)


JOURS_OSM = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']


def horaires_osm(oh):
    """Parse simplifie de opening_hours : {jour: [(debut, fin), ...]} ou None si illisible."""
    if not oh: return None
    if oh.strip() == '24/7': return {j: [(0, 1439)] for j in range(1, 8)}
    res = {}
    for regle in oh.split(';'):
        regle = regle.strip()
        m = re.match(r'^((?:[A-Z][a-z](?:-[A-Z][a-z])?,?\s*)+)\s*(.*)$', regle)
        if not m: continue
        jours = set()
        for part in re.split(r'\s*,\s*', m.group(1).strip()):
            if '-' in part:
                a, b = part.split('-')
                if a in JOURS_OSM and b in JOURS_OSM:
                    ia, ib = JOURS_OSM.index(a), JOURS_OSM.index(b)
                    jours.update(range(ia + 1, ib + 2))
            elif part in JOURS_OSM:
                jours.add(JOURS_OSM.index(part) + 1)
        plages = re.findall(r'(\d\d:\d\d)-(\d\d:\d\d)', m.group(2))
        for j in jours:
            if re.search(r'\b(off|closed)\b', m.group(2)):
                res[j] = []
            else:
                res[j] = [(hm(a), hm(b)) for a, b in plages]
    return res or None


def clip(creneaux, oh):
    """Restreint des creneaux aux horaires d'ouverture."""
    if oh is None: return creneaux
    out = []
    for c in creneaux:
        for j in c['j']:
            for a, b in oh.get(j, []):
                d, f = max(hm(c['d']), a), min(hm(c['f']), b)
                if f - d >= 30:
                    out.append(dict(c, j=[j], d=fmt(d), f=fmt(f)))
    # regroupe les jours identiques
    grp = {}
    for c in out:
        k = (c['d'], c['f'], c['l'], c['p'])
        grp.setdefault(k, []).extend(c['j'])
    return [cr(sorted(set(j)), d, f, l, p) for (d, f, l, p), j in grp.items()]


# ---------------------------------------------------------------- sources
def education():
    r = requests.get('https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-annuaire-education/exports/json',
                     params={'where': 'code_commune="92050" and etat="OUVERT"'}, headers=UA, timeout=60)
    r.raise_for_status(); return r.json()


def calendrier():
    r = requests.get('https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/exports/json',
                     params={'where': 'location="Versailles" and (annee_scolaire="2026-2027" or annee_scolaire="2027-2028")'},
                     headers=UA, timeout=60)
    r.raise_for_status()
    vu, out = set(), []
    for x in sorted(r.json(), key=lambda x: x['start_date']):
        if x.get('population') == 'Enseignants' or x['description'].startswith('Début'): continue
        k = (x['description'], x['start_date'][:10])
        if k in vu: continue
        vu.add(k)
        # dates de l'API en UTC : minuit heure de Paris du 1er jour de vacances et du jour de reprise
        def paris(s):
            dt = date.fromisoformat(s[:10])
            return dt + timedelta(1) if int(s[11:13]) >= 20 else dt
        d1, reprise = paris(x['start_date']), paris(x['end_date'])
        out.append({'nom': x['description'], 'd': d1.isoformat(), 'f': max(reprise - timedelta(1), d1).isoformat()})
    return out


OVERPASS = """[out:json][timeout:120];
area["ref:INSEE"="92050"]["admin_level"="8"]->.a;
(
 nwr["shop"~"^(supermarket|convenience)$"](area.a);
 nwr["railway"="station"](area.a);
 nwr["amenity"~"^(marketplace|townhall|post_office|hospital|university|library|community_centre|theatre|music_venue)$"](area.a);
 nwr["office"~"^(government|employment_agency)$"](area.a);
 nwr["leisure"~"^(sports_centre|stadium|park)$"]["name"](area.a);
);
out center tags;"""


CACHE_OSM = os.path.join(ICI, 'cache_osm.json')


def osm():
    """Reponse Overpass, gardee dans cache_osm.json (supprimer le fichier pour rafraichir)."""
    if os.path.exists(CACHE_OSM):
        return json.load(open(CACHE_OSM, encoding='utf-8'))['elements']
    for url in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'] * 2:
        try:
            r = requests.post(url, data={'data': OVERPASS}, headers=UA, timeout=180)
            r.raise_for_status()
            open(CACHE_OSM, 'w', encoding='utf-8').write(r.text)
            return r.json()['elements']
        except Exception as e:
            print('Overpass indisponible :', url, e, file=sys.stderr)
    raise SystemExit('Overpass injoignable : réessayer plus tard')


def jours_feries(annees):
    out = []
    for y in annees:
        a, b, c = y % 19, y // 100, y % 100
        d, e = b // 4, b % 4
        g = (8 * b + 13) // 25
        h = (19 * a + b - d - g + 15) % 30
        i, k = c // 4, c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 19 * l) // 433
        mois = (h + l - 7 * m + 90) // 25
        jour = (h + l - 7 * m + 33 * mois + 19) % 32
        paques = date(y, mois, jour)

        for nom, dt in [('Jour de l\'an', date(y, 1, 1)), ('Lundi de Pâques', paques + timedelta(1)),
                        ('Fête du travail', date(y, 5, 1)), ('Victoire 1945', date(y, 5, 8)),
                        ('Ascension', paques + timedelta(39)), ('Lundi de Pentecôte', paques + timedelta(50)),
                        ('Fête nationale', date(y, 7, 14)), ('Assomption', date(y, 8, 15)),
                        ('Toussaint', date(y, 11, 1)), ('Armistice', date(y, 11, 11)), ('Noël', date(y, 12, 25))]:
            out.append({'nom': nom, 'd': dt.isoformat()})
    return sorted(out, key=lambda x: x['d'])


# ---------------------------------------------------------------- construction
def main():
    col = json.load(open(COLLAGE, encoding='utf-8'))
    QS = col['quartiers']
    lieux = []

    def ajoute(cat, nom, lat, lon, a='', creneaux=(), note='', src='', **kw):
        q = QUARTIER_FORCE.get(norm(nom)) or quartier(lat, lon, QS)
        l = {'id': '', 'cat': cat, 'nom': nom, 'a': a, 'lat': round(lat, 6), 'lon': round(lon, 6),
             'q': q, 'b': Q2B.get(q), 'cr': list(creneaux), 'note': note, 'src': src}
        l.update(kw); lieux.append(l); return l

    # -- ecoles : maternelle + elementaire de meme nom fusionnees en groupe scolaire
    edu = education()
    ecoles = {}
    for x in edu:
        nom, t = x['nom_etablissement'], x['type_etablissement']
        if 'danse' in nom.lower() or t not in ('Ecole', 'Collège', 'Lycée'): continue
        if t == 'Ecole':
            base = re.sub(r"^Ecole (maternelle|[ée]l[ée]mentaire|primaire)( d'application)? (publique|priv[ée]e)?\s*", '', nom, flags=re.I)
            base = re.sub(r"\s+[AB]$|de l'Institut.*$|de Nanterre$", '', base).strip()
            if base.isdigit(): base = 'privée ' + base
            k = norm(base) + '|' + x['statut_public_prive']
            g = ecoles.setdefault(k, {'base': base, 'xs': []}); g['xs'].append(x)
        elif t == 'Collège':
            if 'adapté' in nom: continue          # SEGPA : meme adresse que le college
            ajoute('college', nom.replace('Ecole secondaire privée de l\'Institut d\'enseignement', 'Collège privé'),
                   x['position']['lat'], x['position']['lon'], x['adresse_1'],
                   [cr(LV, '07:50', '08:15', 'entrée', 1), cr(LV, '16:25', '17:35', 'sorties (selon emploi du temps)', 1)],
                   'Élèves mineurs : peu de parents. Utile surtout pour des tracts « parents d’élèves ».'
                   + (' Éducation prioritaire ' + x['appartenance_education_prioritaire'] + '.' if x.get('appartenance_education_prioritaire') else ''),
                   'Éducation nationale', scol=True, uai=x['identifiant_de_l_etablissement'])
        else:
            if 'Section' in nom: continue          # sections pro : meme site que le lycee
            ajoute('lycee', nom.replace('Lycée polyvalent Frédéric et Irène Joliot Curie', 'Lycée Joliot-Curie'),
                   x['position']['lat'], x['position']['lon'], x['adresse_1'],
                   [cr(LV, '07:45', '08:15', 'entrée', 2), cr(LV, '11:55', '13:30', 'pause méridienne', 2),
                    cr([1, 2, 4, 5], '16:55', '18:05', 'sorties', 1)],
                   'Primo-votants (terminale, BTS) : rappeler l’inscription sur les listes électorales.',
                   'Éducation nationale', scol=True, uai=x['identifiant_de_l_etablissement'])
    for g in ecoles.values():
        xs = g['xs']
        mat = any(x.get('ecole_maternelle') == 1 for x in xs)
        ele = any(x.get('ecole_elementaire') == 1 for x in xs)
        prive = xs[0]['statut_public_prive'] == 'Privé'
        niveaux = 'maternelle + élémentaire' if mat and ele else ('maternelle' if mat else 'élémentaire')
        nom = ('Groupe scolaire ' if mat and ele and len(xs) > 1 else 'École ') + g['base']
        lat = sum(x['position']['lat'] for x in xs) / len(xs)
        lon = sum(x['position']['lon'] for x in xs) / len(xs)
        rep = sorted({x['appartenance_education_prioritaire'] for x in xs if x.get('appartenance_education_prioritaire')})
        note = niveaux.capitalize() + (' · privée' if prive else '') + (' · ' + '/'.join(rep) if rep else '') + '. '
        note += ('Parents de maternelle : ils accompagnent jusqu’à la classe, le meilleur créneau. '
                 if mat else 'Parents moins présents en élémentaire à partir du CE2. ')
        if prive: note += 'Horaires d’une école privée : à vérifier. '
        ajoute('ecole', nom, lat, lon, xs[0]['adresse_1'],
               [cr(LMJV, '08:30', '08:50', 'entrée (classe à 8h45)', 3),
                cr(LMJV, '11:55', '12:10', 'sortie de midi (hors cantine)', 1),
                cr(LMJV, '16:20', '16:45', 'sortie (16h30)', 3)],
               note.strip(), 'Éducation nationale', scol=True, uai=[x['identifiant_de_l_etablissement'] for x in xs],
               aff=250 if mat and ele else (130 if mat else 100))

    # -- OSM
    els = osm()
    def c_of(e):
        return (e['lat'], e['lon']) if 'lat' in e else (e['center']['lat'], e['center']['lon'])
    def adr(t):
        return ' '.join(x for x in [t.get('addr:housenumber', ''), t.get('addr:street', '')] if x)

    # gares
    vu = {}
    for e in els:
        t = e['tags']
        if t.get('railway') != 'station': continue
        n = norm(t.get('name'))
        if n in vu: continue
        lat, lon = c_of(e); vu[n] = 1
        nom = t['name'].replace(' - ', '-').replace('Nanterre La Folie', 'Nanterre-La Folie')
        lignes = {'nanterre prefecture': 'RER A', 'nanterre ville': 'RER A', 'nanterre universite': 'RER A + ligne L',
                  'nanterre la folie': 'RER E'}.get(n, '')
        p = 2 if 'folie' in n else 3
        crs = [cr(LV, '07:00', '09:00', 'départs vers Paris / La Défense', p),
               cr(LV, '17:00', '19:30', 'retours du travail', p)]
        note = lignes + '. Se placer côté sortie de ville, pas sur le quai.'
        if 'universite' in n:
            crs.append(cr(LV, '11:45', '13:45', 'flux étudiants', 2))
            note += ' Énorme flux étudiant vers le campus le matin.'
        if 'ville' in n:
            crs.append(cr([3, 6], '09:30', '12:30', 'marché de la Gare à côté', 2))
        if 'folie' in n:
            note += ' Gare récente (RER E), encore peu fréquentée.'
        ajoute('gare', 'Gare ' + nom, lat, lon, adr(t), crs, note, 'OSM')

    # marches (jours : nanterre.fr ; heures : ot-nanterre.fr)
    marches = {norm(e['tags'].get('name')): c_of(e) for e in els if e['tags'].get('amenity') == 'marketplace'}
    def mpos(cle, adresse):
        return marches.get(cle) or ban(adresse)[:2]
    M = [("Marché du Centre", 'marche du centre', 'Place du Maréchal Foch', [2, 4, 7], '13:30',
          'Le plus grand marché : ~65 commerçants alimentaires, ~30 non alimentaires. Dimanche = la plus grosse affluence.'),
         ("Marché de la Gare", 'marche de la gare', 'Avenue Benoît Frachon', [3, 6], '13:30',
          'À côté de la gare Nanterre-Ville. ~24 commerçants alimentaires, ~70 non alimentaires.'),
         ("Marché Pablo-Picasso", '', '5 Allée des Trois Musiciens', [3, 6], '13:30',
          'Halle du Parc Sud. 18 commerçants alimentaires, ~30 non alimentaires.'),
         ("Marché Préfecture (Charles-de-Gaulle)", 'marche charles de gaulle', 'Esplanade Charles de Gaulle', [2, 5, 7], '14:00',
          'Entre la sortie du RER Nanterre-Préfecture et le parc André-Malraux. 11 commerçants alimentaires, ~20 non alimentaires.')]
    for nom, cle, a, jours, fin, note in M:
        lat, lon = mpos(cle, a + ' Nanterre')
        ajoute('marche', nom, lat, lon, a,
               [cr(jours, '09:00', '12:30', 'marché (pic 10h–12h)', 3)], note, 'nanterre.fr / ot-nanterre.fr')
    # Petit-Nanterre : pas de marche dans le quartier, celui des habitants est juste de
    # l'autre cote de la limite, a Colombes (rattache a la boucle PN, la plus proche)
    pc = ban('485 rue Gabriel Péri', '92025')
    ajoute('marche', 'Marché du Petit-Colombes', pc[0], pc[1], '485–497 rue Gabriel-Péri, Colombes',
           [cr([2, 5], '09:00', '12:30', 'marché (8h–12h45)', 3), cr([7], '09:00', '13:00', 'marché (8h–13h30)', 3)],
           'À Colombes, à la limite du Petit-Nanterre : c’est le marché des habitants du quartier.',
           'colombes.fr')

    # supermarches
    GRANDS = ('lidl', 'aldi', 'leclerc', 'intermarche', 'carrefour market', 'monoprix', 'hyper halal', 'sitis')
    PROXI = ('franprix', 'carrefour city', 'monop', 'coccinelle', 'g20', 'naturalia', 'biocoop', 'yokoo')
    for e in els:
        t = e['tags']
        if t.get('shop') not in ('supermarket', 'convenience'): continue
        n = norm(t.get('brand') or t.get('name'))
        grand = any(g in n for g in GRANDS)
        if not grand and not any(p in n for p in PROXI): continue
        if t['shop'] == 'convenience' and not any(b in n for b in ('franprix', 'carrefour', 'monop', 'coccinelle')): continue
        lat, lon = c_of(e)
        oh = horaires_osm(t.get('opening_hours')) or {j: [(hm('08:30'), hm('20:30'))] for j in range(1, 7)}
        if grand:
            base = [cr(LV, '17:30', '19:30', 'sortie du travail', 2),
                    cr([6], '10:00', '12:30', 'courses du samedi', 3), cr([6], '15:00', '18:30', 'samedi après-midi', 2),
                    cr([7], '10:00', '12:30', 'dimanche matin', 2)]
            note = 'Grande surface. Affluence estimée (profil type), à confirmer avec les « heures d’affluence » Google Maps.'
        else:
            base = [cr(LV, '12:00', '13:30', 'pause déjeuner', 1), cr(LV, '18:00', '20:00', 'sortie du travail', 2),
                    cr([6], '10:30', '13:00', 'samedi matin', 2), cr([7], '10:00', '12:30', 'dimanche matin', 1)]
            note = 'Magasin de proximité : flux continu mais petit. Affluence estimée, à confirmer.'
        crs = clip(base, oh)
        nom = t.get('name') or t.get('brand')
        a = adr(t)
        ajoute('super', nom, lat, lon, a, crs, note + ' Vérifier que le gérant ne s’y oppose pas (trottoir = espace public).',
               'OSM', oh=t.get('opening_hours', ''))

    # services publics, centres sociaux, sante, culture, parcs, stades
    SERV = {
        'france travail': ([cr([1, 2, 3, 4], '09:00', '12:00', 'file d’attente du matin', 2)], 'Demandeurs d’emploi : public très concerné par nos propositions.'),
        'cpam des hauts de seine': ([cr(LV, '08:30', '11:30', 'accueil du matin', 1)], 'Siège départemental de la CPAM.'),
        'prefecture des hauts de seine': ([cr(LV, '08:30', '11:30', 'file d’attente du matin', 1)], 'Beaucoup de démarches de titres de séjour : public souvent non électeur.'),
        'hotel de ville': ([cr([6], '09:00', '12:30', 'samedi matin', 1)], 'Parvis de l’hôtel de ville. Éviter les jours de mariage.'),
        'maison de l emploi': ([cr(LV, '09:00', '12:00', 'matin', 1)], ''),
    }
    for e in els:
        t = e['tags']; n = norm(t.get('name'))
        lat, lon = c_of(e) if ('lat' in e or 'center' in e) else (None, None)
        if lat is None: continue
        if n in SERV:
            crs, note = SERV.pop(n)
            ajoute('service', t['name'], lat, lon, adr(t), crs, note, 'OSM')
        elif t.get('amenity') == 'townhall' and 'quartier' in n or n.startswith('antenne de quartier'):
            oh = horaires_osm(t.get('opening_hours'))
            crs = clip([cr([1, 2, 3, 4, 5, 6], '09:00', '12:00', 'accueil du matin', 1)], oh) if oh else \
                [cr([1, 2, 3, 4, 5, 6], '09:00', '12:00', 'accueil du matin (horaires à vérifier)', 1)]
            ajoute('service', t['name'], lat, lon, adr(t), crs, 'Mairie de quartier : passage régulier, public local.', 'OSM')
        elif t.get('amenity') == 'post_office' and n.startswith('nanterre') or n == 'bureau de poste du chemin de l ile':
            oh = horaires_osm(t.get('opening_hours'))
            crs = clip([cr([6], '09:00', '12:00', 'samedi matin', 1), cr(LV, '17:00', '19:00', 'fin de journée', 1)], oh)
            if crs:
                ajoute('service', 'La Poste — ' + t['name'].replace('Nanterre ', ''), lat, lon, adr(t), crs, 'File d’attente.', 'OSM')
        elif t.get('amenity') == 'community_centre' and re.search(r'centre social|maison pour tous|maison du chemin', n):
            oh = horaires_osm(t.get('opening_hours'))
            crs = clip([cr([1, 2, 3, 4, 5, 6], '09:30', '12:00', 'accueil', 1), cr(LV, '16:30', '18:30', 'activités de fin de journée', 1)], oh)
            ajoute('social', t['name'], lat, lon, adr(t), crs,
                   'Lieu de vie du quartier : plutôt pour se faire connaître, déposer une affiche ou repérer les événements.', 'OSM')
        elif n == 'hopital max fourestier':
            ajoute('sante', 'Hôpital Max-Fourestier (CASH)', lat, lon, adr(t) or '403 avenue de la République',
                   [cr(SEM, '13:30', '15:00', 'relève des équipes + début des visites', 1)],
                   'Personnel hospitalier et visiteurs. Rester devant l’entrée, hors de l’enceinte.', 'OSM')
        elif n in ('universite paris nanterre',):
            ajoute('univ', 'Université Paris Nanterre', lat, lon, '200 avenue de la République',
                   [cr(LV, '08:00', '09:45', 'arrivées depuis la gare', 3), cr(LV, '11:45', '14:00', 'pause déjeuner (restos U)', 3),
                    cr([1, 2, 3, 4], '16:30', '18:30', 'sorties de cours', 2)],
                   '~35 000 étudiants. Allée entre la gare Nanterre-Université et le campus ; restos U à midi. '
                   'Coordonner avec le groupe étudiant (Jeunes insoumis·es) s’il existe.', 'OSM', scol=False)
        elif t.get('amenity') == 'music_venue' and 'arena' in n:
            ajoute('culture', t['name'] + ' (ex-Paris La Défense Arena)', lat, lon, adr(t), [],
                   'Concerts, Racing 92, tennis : public venu de toute l’Île-de-France, peu d’électeurs nanterriens. Voir l’agenda.', 'OSM')
        elif n in ('theatre des amandiers',):
            ajoute('culture', 'Théâtre Nanterre-Amandiers', lat, lon, adr(t), [cr([2, 3, 4, 5, 6], '19:30', '20:30', 'avant les représentations', 1)],
                   'Public cultivé, en partie extérieur à la ville.', 'OSM')
        elif t.get('amenity') == 'library' and n.startswith('mediatheque') or n.startswith('bibliotheque municipale'):
            oh = horaires_osm(t.get('opening_hours'))
            crs = clip([cr([3, 6], '10:00', '12:30', 'matinée', 1), cr([3, 6], '14:00', '18:00', 'après-midi', 1)], oh)
            ajoute('culture', t['name'][0].upper() + t['name'][1:], lat, lon, adr(t), crs, 'Familles le mercredi et le samedi.', 'OSM')
        elif t.get('leisure') == 'park' and n in ('parc andre malraux', 'parc du chemin de l ile', 'parc des anciennes mairies',
                                                   'parc des chenevreux', 'parc urbain hoche'):
            ajoute('parc', t['name'], lat, lon, '', [cr([3], '14:30', '18:00', 'mercredi après-midi (enfants)', 1),
                                                     cr([6, 7], '14:00', '18:30', 'week-end, beau temps', 2)],
                   'Familles et promeneurs quand il fait beau. Point = centre du parc : se placer aux entrées principales.', 'OSM')
        elif t.get('leisure') in ('sports_centre', 'stadium') and re.match(r'(stade|complexe sportif) ', n):
            ajoute('stade', t['name'], lat, lon, adr(t), [cr([6], '09:30', '12:30', 'matchs jeunes', 1), cr([7], '09:30', '12:30', 'matchs', 1)],
                   'Parents au bord du terrain : dépend du calendrier des clubs (ES Nanterre…), à vérifier.', 'OSM')
    # ecoles superieures privees : etablissements de la commune dans les effectifs etudiants du
    # ministere (rentree 2025, data.enseignementsup-recherche.gouv.fr), position fournie par le
    # jeu de donnees. Frequentation : environ un quart des inscrits present sur un creneau.
    for nom, lat, lon, inscrits, note in ECOLES_SUP:
        ajoute('sup', nom, lat, lon, '',
               [cr(LV, '08:15', '09:15', 'arrivées', 2), cr(LV, '12:00', '14:00', 'pause déjeuner', 3),
                cr([1, 2, 3, 4], '17:00', '18:30', 'sorties de cours', 2)],
               note, 'MESR, effectifs 2025', aff=max(50, int(round(inscrits / 4, -1))), inscrits=inscrits)

    # Stade Gabriel-Peri (absent d'OSM sous ce nom) : lieu de la Fete de l'engagement
    gp = ban('57 avenue de la Liberté Nanterre')
    ajoute('stade', 'Stade Gabriel-Péri', gp[0], gp[1], '57 avenue de la Liberté',
           [cr([6], '09:30', '12:30', 'matchs jeunes', 1), cr([7], '09:30', '12:30', 'matchs', 1)],
           'Accueille la Fête de l’engagement associatif début septembre.', 'BAN')
    if SERV: print('services introuvables dans OSM :', list(SERV), file=sys.stderr)

    # -- adresses manquantes : adresse la plus proche (BAN), un repere et pas l'adresse officielle
    for l in lieux:
        if re.search(r'[a-zA-Z]', l['a'] or ''): continue
        try:
            r = requests.get('https://api-adresse.data.gouv.fr/reverse/', params={'lat': l['lat'], 'lon': l['lon'], 'limit': 1},
                             headers=UA, timeout=30)
            p = r.json()['features'][0]['properties']
            l['a'] = p['name']; l['aProche'] = True
        except Exception as e:
            print('adresse introuvable :', l['nom'], e, file=sys.stderr)

    # -- identifiants
    pref = {'ecole': 'E', 'lycee': 'L', 'college': 'C', 'univ': 'U', 'sup': 'A', 'gare': 'G', 'marche': 'M', 'super': 'S',
            'service': 'P', 'social': 'X', 'parc': 'J', 'stade': 'T', 'sante': 'H', 'culture': 'K'}
    ordre = list(pref)
    for l in lieux:
        l.setdefault('aff', AFFLUENCE.get(norm(l['nom']), AFFLUENCE_DEFAUT.get(l['cat'], 100)))
    lieux.sort(key=lambda l: (ordre.index(l['cat']), [b['id'] for b in BOUCLES].index(l['b']) if l['b'] else 9, norm(l['nom'])))
    cpt = {}
    for l in lieux:
        cpt[l['cat']] = cpt.get(l['cat'], 0) + 1
        l['id'] = pref[l['cat']] + str(cpt[l['cat']])
    ids = {norm(l['nom']): l['id'] for l in lieux}

    # -- evenements
    def ev(nom, d, f, h, statut, b=None, lieu='', pos=None, refs=(), note='', src='', periode=''):
        x = {'nom': nom, 'd': d, 'f': f or d, 'h': h, 'statut': statut, 'b': b, 'lieu': lieu, 'refs': list(refs),
             'note': note, 'src': src, 'periode': periode}
        if pos: x['lat'], x['lon'] = pos[0], pos[1]
        if pos and not b:
            q = quartier(pos[0], pos[1], QS); x['b'] = Q2B.get(q)
        return x
    lid = lambda n: ids[norm(n)]
    tous_marches = [l['id'] for l in lieux if l['cat'] == 'marche' and not l.get('aConfirmer')]
    ecl = next(l for l in lieux if norm(l['nom']) == 'parc du chemin de l ile')
    asayad = ban('56 rue Abdelmalek Sayad Nanterre')
    parc_ec = next((l for l in lieux if 'p arc en ciel' in norm(l['nom'])), None)
    groues = ban('69 rue de la Garenne Nanterre')
    E = [
        ev('Animations de Noël des marchés', '2026-12-11', '2026-12-13', 'matinées de marché', 'confirmé', refs=tous_marches,
           lieu='Les 4 marchés', note='2 000 € de bons d’achat, chocolats pour les enfants : affluence renforcée.', src='nanterre.fr (fiches marchés)',
           periode='chaque année mi-décembre'),
        ev('Fête de l’hiver Centre / Vieux-Pont', '2026-12-05', '2026-12-12', 'samedi après-midi', 'à confirmer', b='CVP',
           lieu='Centre de loisirs Abdelmalek-Sayad (édition 2025)', pos=asayad[:2],
           note='Édition 2025 : samedi 6 décembre. Date 2026 non publiée au 29 octobre.', src='Nanterre Info déc. 2025',
           periode='début décembre'),
        ev('Fête de l’hiver Parc Sud', '2026-12-05', '2026-12-12', 'après-midi', 'à confirmer', b='PSN',
           lieu='Centre social P’Arc en Ciel', pos=(parc_ec['lat'], parc_ec['lon']) if parc_ec else None,
           refs=[parc_ec['id']] if parc_ec else [],
           note='Éditions précédentes : 7 décembre 2024, puis 24 janvier (15h–19h).', src='nanterre.fr', periode='décembre ou janvier'),
        ev('Fêtes de l’hiver Chemin-de-l’Île et Mont-Valérien', '2026-12-12', '2026-12-19', 'samedi', 'à confirmer', b=None,
           lieu='Lieux à confirmer', note='Édition 2024 : samedi 14 décembre pour les deux quartiers.', src='nanterre.fr',
           periode='mi-décembre'),
        ev('Fête des bords de Seine + festival EcoZone', '2026-05-23', None, '10h30–18h30', 'passé', b='CI',
           lieu="Parc du Chemin-de-l'Île", pos=(ecl['lat'], ecl['lon']), refs=[ecl['id']],
           note='15e édition en 2026, ~70 stands, très fréquentée. EcoZone se poursuit toute la semaine.', src='nanterre.fr',
           periode='fin mai, un samedi'),
        ev('Festival Parade(s) — arts de la rue', '2026-06-05', '2026-06-07', 'après-midi et soirée', 'passé', b='CVP',
           lieu='Centre-ville principalement', note='Spectacles gratuits, gros public familial.', src='lestroiscoups.fr',
           periode='début juin'),
        ev('Les Groues en fête', '2026-06-20', None, '11h–22h', 'passé', lieu='Vive les Groues, 69 rue de la Garenne',
           pos=groues[:2], src='nanterre.fr', periode='juin'),
        ev('Fête de la musique', '2026-06-21', None, '11h–minuit', 'passé', lieu='Toute la ville',
           note='Édition 2026 annulée (canicule).', src='nanterre.fr', periode='21 juin'),
        ev('Fête nationale (bal, concert, feu d’artifice)', '2026-07-13', None, 'midi à 23h', 'passé', lieu='Plage de Nanterre',
           note='Date et lieu 2026 issus d’un site non officiel.', src='festivalenfrance.com', periode='13 juillet'),
        ev('Fête de l’engagement associatif', '2026-09-05', None, '11h–18h', 'passé', lieu='Stade Gabriel-Péri (entrée 57 av. de la Liberté)',
           pos=gp[:2], refs=[lid('Stade Gabriel-Péri')],
           note='~200 associations et clubs : inscriptions aux activités, énorme passage de familles. Prévoir un stand ?',
           src='nanterre.fr', periode='premier samedi de septembre'),
    ]

    # -- selection validee le 2026-10-29 : les identifiants des lieux gardes ne changent pas
    def garde(l):
        if l['cat'] in CATS_RETIREES: return False
        if l['cat'] == 'service': return norm(l['nom']) == 'france travail'
        if l['cat'] == 'super': return (norm(l['nom']), norm(l['a'])) in SUPERS_GARDES
        return True
    lieux = [l for l in lieux if garde(l)]
    gardes = {l['id'] for l in lieux}
    for e in E: e['refs'] = [r for r in e['refs'] if r in gardes]
    cats = {k: v for k, v in CATEGORIES.items() if any(l['cat'] == k for l in lieux)}

    out = {
        'maj': date.today().isoformat(), 'version': 1,
        'horairesEcoles': 'Écoles publiques : 8h45–12h et 13h45–16h30, lundi, mardi, jeudi, vendredi (nanterre.fr, rentrée 2026).',
        'boucles': BOUCLES, 'categories': cats,
        'vacances': calendrier(), 'feries': jours_feries([2026, 2027, 2028]),
        'quartiers': QS, 'evenements': E, 'lieux': lieux,
    }
    NL = '\n'
    head = ',\n'.join(' %s: %s' % (json.dumps(k, ensure_ascii=False), json.dumps(v, ensure_ascii=False))
                      for k, v in out.items() if k not in ('lieux', 'evenements', 'quartiers'))
    txt = ('{' + NL + head + ',' + NL + ' "quartiers": ' + json.dumps(QS, ensure_ascii=False) + ',' + NL +
           ' "evenements": [' + NL + (',' + NL).join('  ' + json.dumps(x, ensure_ascii=False) for x in E) + NL + ' ],' + NL +
           ' "lieux": [' + NL + (',' + NL).join('  ' + json.dumps(x, ensure_ascii=False) for x in lieux) + NL + ' ]' + NL + '}' + NL)
    open(os.path.join(RACINE, 'lieux.json'), 'w', encoding='utf-8', newline='\n').write(txt)
    par = {}
    for l in lieux: par[(l['cat'], l['b'])] = par.get((l['cat'], l['b']), 0) + 1
    print(len(lieux), 'lieux,', len(E), 'événements')
    for c in cats:
        print(' ', c.ljust(8), ' '.join('%s:%d' % (b['id'], par.get((c, b['id']), 0)) for b in BOUCLES), ' hors:', par.get((c, None), 0))


if __name__ == '__main__':
    main()
