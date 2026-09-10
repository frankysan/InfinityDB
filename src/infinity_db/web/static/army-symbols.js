const armySymbols = new Map([
  [101, "PanOceania/panoceania-1.1.svg"], [102, "PanOceania/shock-army-of-acontecimento-1.1.svg"],
  [103, "PanOceania/military-orders-1.1.svg"], [104, "PanOceania/neoterran-capitaline-army-1.1.svg"],
  [105, "PanOceania/varuna-immediate-reaction-division-1.1.svg"], [106, "PanOceania/svalarheima-s-winter-force-1.1.svg"],
  [107, "PanOceania/kestrel-colonial-force-1.1.5.svg"], [199, "PanOceania/code-capital-1.1.5.svg"],
  [201, "Yu Jing/yu-jing-1.1.svg"], [202, "Yu Jing/imperial-service-1.1.svg"],
  [204, "Yu Jing/invincible-army-1.1.5.svg"], [205, "Yu Jing/white-banner-1.1.svg"], [299, "Yu Jing/daebak-force-1.1.5.svg"],
  [301, "Ariadna/ariadna-1.1.svg"], [302, "Ariadna/caledonian-highlander-army-1.1.svg"],
  [303, "Ariadna/force-de-reponse-rapide-merovingienne-1.1.svg"], [304, "Ariadna/usariadna-1.1.svg"],
  [305, "Ariadna/tartary-1.1.5.svg"], [306, "Ariadna/kosmoflot-1.1.svg"], [399, "Ariadna/l-equipe-argent-1.1.5.svg"],
  [401, "Haqqislam/haqqislam-1.1.svg"], [402, "Haqqislam/hassassin-bahram-1.1.svg"], [403, "Haqqislam/qapu-khalqi-1.1.svg"],
  [404, "Haqqislam/ramah-taskforce-1.1.svg"], [499, "Haqqislam/melek-reaction-group-1.1.5.svg"],
  [501, "Nomads/nomads-1.1.svg"], [502, "Nomads/corregidor-1.1.svg"], [503, "Nomads/bakunin-1.1.svg"],
  [504, "Nomads/tunguska-1.1.svg"], [599, "Nomads/vipera-pursuit-force-1.1.5.svg"],
  [601, "Combined Army/combined-army-2.0.svg"], [602, "Combined Army/morat-2.0.svg"],
  [603, "Combined Army/shasvastii-2.0.2.svg"], [604, "Combined Army/onyx-2.0.svg"],
  [605, "Combined Army/next-wave.svg"],
  [699, "Combined Army/the-exrah-comissariat-2.0.svg"], [701, "Aleph/aleph-1.1.svg"],
  [702, "Aleph/steel-phalanx-1.1.svg"], [703, "Aleph/operations-1.1.svg"], [799, "Aleph/ank-program-1.1.5.svg"],
  [801, "Tohaa/tohaa-1.1.svg"], [899, "Tohaa/deras-kaar-1.1.svg"],
  [901, "NA2/non-aligned-armies-1.1.svg"], [902, "NA2/druze-1.1.svg"],
  [904, "NA2/ikari-1.1.svg"], [905, "NA2/starco-free-company-of-the-star-1.1.svg"],
  [908, "NA2/dahshat-1.1.svg"], [909, "NA2/white-company-1.1.svg"],
  [998, "NA2/contracted-back-up.svg"], [999, "NA2/contracted-back-up-1.1.5.svg"],
  [1001, "O-12/o-12-1.1.svg"], [1002, "O-12/starmada-1.1.5.svg"], [1003, "O-12/torchlight-brigade-1.1.svg"],
  [1099, "O-12/teams-gladius-1.1.svg"], [1101, "JSA/jsa-1.1.svg"], [1102, "JSA/shindenbutai-1.1.5.svg"],
  [1103, "JSA/oban-1.1.5.svg"], [1199, "JSA/hayabusa-reconstructed-transparent.svg"],
]);

export function armySymbolPath(armyId) {
  const symbol = armySymbols.get(armyId);
  return symbol && `/static/army-symbols/${encodeURI(symbol)}`;
}
