// Fusionne les quartiers de lieux.json en une zone par boucle, plus le contour de la ville.
//
//     npm install @turf/turf@7      (une fois, n'importe où : passer le dossier via NODE_PATH)
//     node outils/zones_boucles.cjs
//
// Ecrit zones.json a la racine. A relancer seulement si les boucles ou les quartiers changent.
// Les limites de quartiers reprises de Collage ne partagent pas toujours exactement leurs
// sommets : chaque quartier est grossi de 15 m avant la fusion puis reduit d'autant, ce qui
// referme les interstices sans deplacer le contour exterieur.
const fs = require('fs');
const path = require('path');
const turf = require('@turf/turf');

const RACINE = path.join(__dirname, '..');
const d = JSON.parse(fs.readFileSync(path.join(RACINE, 'lieux.json'), 'utf8'));
const Q = Object.fromEntries(d.quartiers);
const MARGE = 0.015; // km

const versTurf = rings => turf.polygon(rings.map(r => {
  const c = r.map(([lat, lon]) => [lon, lat]);
  if (c[0][0] !== c.at(-1)[0] || c[0][1] !== c.at(-1)[1]) c.push(c[0]);
  return c;
}));
const versLeaflet = geom => (geom.type === 'Polygon' ? [geom.coordinates] : geom.coordinates)
  .map(poly => poly.map(ring => ring.map(([lon, lat]) => [+lat.toFixed(5), +lon.toFixed(5)])));

function fusion(noms) {
  const fs_ = noms.map(n => turf.buffer(versTurf(Q[n][0] ? Q[n] : [Q[n]]), MARGE, { units: 'kilometers' }));
  const u = fs_.length > 1 ? turf.union(turf.featureCollection(fs_)) : fs_[0];
  return turf.simplify(turf.buffer(u, -MARGE, { units: 'kilometers' }), { tolerance: 0.00002, highQuality: true });
}

const zones = d.boucles.map(b => {
  const z = fusion(b.quartiers);
  // point d'etiquette : centre de masse s'il tombe dans la zone, sinon un point interieur
  let p = turf.centerOfMass(z);
  if (!turf.booleanPointInPolygon(p, z)) p = turf.pointOnFeature(z);
  const [lon, lat] = p.geometry.coordinates;
  return { id: b.id, poly: versLeaflet(z.geometry), label: [+lat.toFixed(5), +lon.toFixed(5)] };
});
// contour de la ville : la plus grande partie (les interstices entre quartiers non voisins
// laissent parfois de minuscules morceaux isoles)
const ville = versLeaflet(fusion(d.quartiers.map(q => q[0])).geometry)
  .sort((a, b) => turf.area(versTurf(b)) - turf.area(versTurf(a)))[0];

fs.writeFileSync(path.join(RACINE, 'zones.json'), JSON.stringify({ ville, zones }) + '\n');
console.log(zones.map(z => z.id + ':' + z.poly.length + ' partie(s)').join(' '), '· ville:', ville[0].length, 'sommets');
