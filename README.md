<p align="center">
  <img src="https://raw.githubusercontent.com/olivierouellet/Silo/main/assets/icon.svg" alt="Silo logo" width="128" height="128">
</p>

<h1 align="center">Silo</h1>

<p align="center">How full your grain silos are, in Home Assistant · Le niveau de vos silos à grains, dans Home Assistant</p>

<p align="center"><b><a href="#english">English</a> · <a href="#français">Français</a></b></p>

---

## English

Silo turns a distance sensor at the top of a grain silo or bin into what you want to know: **how full it is, how many tons are in it, and how much to order**.

It has two parts:

| Part | Repository | What it does |
|---|---|---|
| **Silo integration** (`silo`) | this one | Describe each silo once (its shape, rings, roof and hopper, and what it holds) and get sensors for the fill level, grain height, volume, weight and room left. |
| **Silo Card** | [Silo-Card](https://github.com/olivierouellet/Silo-Card) | A dashboard card that draws the silo to scale, section by section, filled to the level. Pick the integration's *Fill level* sensor and that's all: the card reads the silo from it. |

The card also works without the integration, with the silo described in the card. The integration is what gives you history and automations, say, a notification when a bin needs filling.

### The sensor

Any sensor that measures the distance down to the grain (or the grain's height) works, in any length unit. Silo Card has a complete [ESPHome example](https://github.com/olivierouellet/Silo-Card/tree/main/examples/esphome) for an ESP32-C3 and a MaxBotix HRXL-MaxSonar-WR ultrasonic sensor: the firmware only measures, so the same firmware fits every silo.

### Setting up a silo

*Settings → Devices & services → Helpers → Create helper → Silo*, or *Add integration → Silo*. Three steps:

1. **The sensor**: the sensor, what it measures, and the unit of the dimensions (m, cm, ft or in).
2. **The shape**: round or square; the diameter; the number of rings and their height; the roof (cone, dome or flat) and the bottom (flat floor or cone hopper, with its outlet). The silo's lowest point is height 0; by default the sensor is at the very top.
3. **The contents**: a grain (its standard bushel weight), your own density, or the manufacturer's capacity, for the weight. The capacity can be the whole silo's or one full ring's (“3 tons a ring”): the hopper and roof then get the weight of their own volume, a cone holding a third of a ring as tall. Units for the weight (t, kg, short tons, lb) and the volume (m³, L, ft³, bushels). Whether full means filled to the eave (the default) or to the peak.

Add one entry per silo. *Configure* changes any of it later; the sensors keep their IDs, and a new unit converts the lengths already entered.

### Sensors

The sensors join the device of the distance sensor (your ESPHome board), or a device of their own.

| Sensor | Unit | |
|---|---|---|
| Fill level | % | Of the capacity; above 100 % when grain fills a roof that isn't part of “full”. Its attributes carry the silo and the grain height, for Silo Card. |
| Grain height | the dimensions' unit | Above the silo's lowest point. |
| Rings filled | — | 0 to the number of rings (4.5 = halfway up the 5th). |
| Grain volume | the volume unit | |
| Grain weight | the weight unit | Only when a grain, density or capacity is set. |
| Room left | the weight unit | What it takes to fill it: the next order. |

The values follow the distance sensor as it changes; when it has no reading, they are unknown.

The sensors use the units entered for the silo. The grain height, and volumes and weights in m³, L, ft³, kg or lb, can be shown in another unit from each sensor's settings in Home Assistant; tonnes, short tons and bushels can't, as Home Assistant has no conversion for them. Silo Card can show its own units whatever the integration uses.

### Installation

**With HACS (recommended)**

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=olivierouellet&repository=Silo&category=integration)

1. In Home Assistant, open **HACS** → **⋮** (top right) → **Custom repositories**.
2. Repository: `https://github.com/olivierouellet/Silo`, type: **Integration**, then **Add**. (The button above does steps 1 and 2 for you.)
3. Search for **Silo**, open it and click **Download**.
4. Restart Home Assistant, then add a silo as above.

**Manual**: copy `custom_components/silo` into your `config/custom_components/` folder and restart Home Assistant.

Then install [Silo Card](https://github.com/olivierouellet/Silo-Card) and add it with the *Fill level* sensor:

```yaml
type: custom:silo-card
entity: sensor.soue_1_ben_2_fill_level
```

### How accurate is it?

The volume is exact for the shape you describe, but grain isn't flat: it heaps into a cone under the fill tube and hollows into a funnel as it empties, and the sensor sees a single spot. Expect the weight to be off by a few percent, more in wide bins. For the weight, the manufacturer's capacity or your own test weight beats the standard bushel weight.

### Development

- `uv venv --python 3.13 && uv pip install -r requirements_test.txt`, then `pytest` and `ruff check && ruff format --check`.
- `geometry.py` is mirrored in Silo Card and both have the same tests: see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

---

## Français

Silo transforme un capteur de distance en haut d’un silo ou d’une cellule à grains en ce que vous voulez savoir : **à quel point il est plein, combien de tonnes il contient, et combien commander**.

Il a deux parties :

| Partie | Dépôt | Ce qu’elle fait |
|---|---|---|
| **Intégration Silo** (`silo`) | celui-ci | Décrivez chaque silo une seule fois (sa forme, ses sections, son toit et sa trémie, et ce qu’il contient) et obtenez des capteurs pour le taux de remplissage, la hauteur du grain, le volume, le poids et la place libre. |
| **Silo Card** | [Silo-Card](https://github.com/olivierouellet/Silo-Card#français) | Une carte de tableau de bord qui dessine le silo à l’échelle, section par section, rempli jusqu’au niveau. Choisissez le capteur *Taux de remplissage* de l’intégration et c’est tout : la carte y lit le silo. |

La carte fonctionne aussi sans l’intégration, avec le silo décrit dans la carte. C’est l’intégration qui vous donne l’historique et les automatisations, par exemple un avis quand une cellule doit être remplie.

### Le capteur

Tout capteur qui mesure la distance jusqu’au grain (ou la hauteur du grain) convient, dans n’importe quelle unité de longueur. Silo Card a un [exemple ESPHome](https://github.com/olivierouellet/Silo-Card/tree/main/examples/esphome) complet pour un ESP32-C3 et un capteur à ultrasons MaxBotix HRXL-MaxSonar-WR : le micrologiciel ne fait que mesurer, donc le même micrologiciel convient à tous les silos.

### Configurer un silo

*Paramètres → Appareils et services → Entrées → Créer une entrée → Silo*, ou *Ajouter une intégration → Silo*. Trois étapes :

1. **Le capteur** : le capteur, ce qu’il mesure, et l’unité des dimensions (m, cm, pi ou po).
2. **La forme** : ronde ou carrée; le diamètre; le nombre de sections et leur hauteur; le toit (cône, dôme ou plat) et le fond (plancher plat ou trémie en cône, avec sa sortie). Le point le plus bas du silo est la hauteur 0; par défaut, le capteur est tout en haut.
3. **Le contenu** : un grain (le poids standard de son boisseau), votre propre masse volumique, ou la capacité du fabricant, pour le poids. La capacité peut être celle du silo entier ou d’une section pleine (« 3 tonnes par section ») : la trémie et le toit prennent alors le poids de leur propre volume, un cône contenant le tiers d’une section de même hauteur. Les unités de poids (t, kg, tonnes courtes, lb) et de volume (m³, L, pi³, boisseaux). Si plein veut dire rempli jusqu’au bas du toit (par défaut) ou jusqu’au sommet.

Ajoutez une entrée par silo. *Configurer* permet de tout changer plus tard; les capteurs gardent leurs identifiants, et une nouvelle unité convertit les longueurs déjà entrées.

### Capteurs

Les capteurs rejoignent l’appareil du capteur de distance (votre module ESPHome), ou un appareil à eux.

| Capteur | Unité | |
|---|---|---|
| Taux de remplissage | % | De la capacité; au-delà de 100 % quand le grain remplit un toit qui ne compte pas dans « plein ». Ses attributs portent le silo et la hauteur du grain, pour Silo Card. |
| Hauteur du grain | l’unité des dimensions | Au-dessus du point le plus bas du silo. |
| Sections remplies | — | De 0 au nombre de sections (4,5 = à mi-hauteur de la 5ᵉ). |
| Volume de grain | l’unité de volume | |
| Poids du grain | l’unité de poids | Seulement avec un grain, une masse volumique ou une capacité. |
| Place libre | l’unité de poids | Ce qu’il faut pour le remplir : la prochaine commande. |

Les valeurs suivent le capteur de distance quand il change; quand il n’a pas de mesure, elles sont inconnues.

Les capteurs utilisent les unités entrées pour le silo. La hauteur du grain, et les volumes et poids en m³, L, pi³, kg ou lb, peuvent s’afficher dans une autre unité depuis les paramètres de chaque capteur dans Home Assistant; pas les tonnes, tonnes courtes ni boisseaux, que Home Assistant ne sait pas convertir. Silo Card peut afficher ses propres unités, quelles que soient celles de l’intégration.

### Installation

**Avec HACS (recommandé)**

[![Ouvrir votre instance Home Assistant et ce dépôt dans HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=olivierouellet&repository=Silo&category=integration)

1. Dans Home Assistant, ouvrez **HACS** → **⋮** (en haut à droite) → **Dépôts personnalisés**.
2. Dépôt : `https://github.com/olivierouellet/Silo`, type : **Integration**, puis **Ajouter**. (Le bouton ci-dessus fait les étapes 1 et 2 pour vous.)
3. Cherchez **Silo**, ouvrez-la et cliquez sur **Télécharger**.
4. Redémarrez Home Assistant, puis ajoutez un silo comme ci-dessus.

**Manuelle** : copiez `custom_components/silo` dans le dossier `config/custom_components/` et redémarrez Home Assistant.

Installez ensuite [Silo Card](https://github.com/olivierouellet/Silo-Card#français) et ajoutez-la avec le capteur *Taux de remplissage* :

```yaml
type: custom:silo-card
entity: sensor.soue_1_ben_2_taux_de_remplissage
```

### Quelle précision?

Le volume est exact pour la forme que vous décrivez, mais le grain n’est pas plat : il forme un cône sous le tuyau de remplissage et un entonnoir quand il se vide, et le capteur n’en voit qu’un point. Le poids peut donc s’écarter de quelques pour cent, davantage dans les grandes cellules. Pour le poids, la capacité du fabricant ou votre propre poids spécifique valent mieux que le poids standard du boisseau.

### Développement

- `uv venv --python 3.13 && uv pip install -r requirements_test.txt`, puis `pytest` et `ruff check && ruff format --check`.
- `geometry.py` a son double dans Silo Card et les deux ont les mêmes tests : voir [CONTRIBUTING.md](CONTRIBUTING.md) et [SECURITY.md](SECURITY.md).
