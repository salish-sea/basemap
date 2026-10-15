# 015 — Landmarks are lighthouses, what the charts mark as conspicuous, and tall radio towers

**Status:** accepted · **Decided:** 2026-10-15 · **Context:** SalishSea.io's `salish-3zok.8`

## Context

People who watch whales from shore or from a boat place them by what they can see: "off Lime Kiln lighthouse", "south of the KVI towers". Peter asked for landmarks like these on the map, starting with lighthouses and prominent radio towers, to help someone looking at the map orient themselves, which matters even though reports rarely name a tower. His examples were the AM towers on Maury Island, the broadcast site on Mount Constitution and the towers of the Tacoma Narrows Bridge.

Protomaps' extract carries almost none of them, and only from zoom 16. OpenStreetMap has them, with the tags nautical charts use: `seamark:type=landmark` marks what a chart shows as conspicuous from the water. Over Washington, OpenStreetMap has about 5,700 masts, towers, chimneys, bridges and lighthouses, most of them cell and lighting masts nobody steers by. The rule has to pick out the few that matter by what they are, because heights are missing for most: none of the Mount Constitution towers has one.

## Decision

**A landmark is** ([scripts/landmarks.py](../scripts/landmarks.py)):

- **a lighthouse**: a light the charts call major, or a `man_made=lighthouse` with a name of its own, as Lime Kiln Point Lighthouse has. The hundreds of minor lights on piles and rocks carry only the name the chart gives them (`seamark:name`) and are left out;
- **a tower**: a radio or television mast or tower that the charts mark as a landmark, or that is 100 m or taller. That takes in the Maury Island and Vashon AM arrays, KVI's tower and the Seattle TV towers, and leaves out cell masts. A charted mast or tower whose tags don't say what it carries counts too when masts named for a station's call sign stand within 500 m of it: that is how the charted tower on Mount Constitution, beside KAFE-FM, KISM-FM, KLYN-FM and KBCB-TV, is known for a radio tower;
- **another landmark**: anything else the charts mark as conspicuous, such as a chimney, a dome, a spire or the Space Needle. Cranes are left out, because they come and go, and so is a charted landmark that carries a light: British Columbia's lights, imported into OpenStreetMap from the US light list, are tagged as landmarks, which would add every minor light's tower.

**Points within 500 m of one another are one landmark**, so the broadcast site on Mount Constitution, which is seven masts and towers, is drawn once. It takes the kind, the name and the height of the most prominent: a lighthouse before a tower before anything else, a named point before an unnamed one, and then the tallest.

**Names come from OpenStreetMap,** cleaned of what is a record's label rather than a place's name: "vts 3669705", "TV" and "(KIRO) 710KHz" are dropped, and "KIRO-TV (Seattle)" becomes "KIRO-TV". A landmark without a name is drawn without a label.

**They are drawn with an icon and, from zoom 11, the name under it.** Lighthouses appear from zoom 9 when named and 11 otherwise, towers from 10 and the rest from 11 or 12. The icons are Maki's lighthouse, communications tower and landmark, which are in the public domain, drawn in slate with a white edge into a sprite of their own ([scripts/sprite.ts](../scripts/sprite.ts)), which the style names beside Protomaps'. The layer sits just above Protomaps' points of interest, so a landmark wins its place before a shop does.

**They come from Geofabrik's extracts** of northern California, Oregon, Washington, British Columbia and Alaska, all of one day, which the Makefile names. They are kept in an archive of their own, `landmarks`, under the ODbL like the rest from OpenStreetMap. Being labels and icons, they are not in the image tiles ([014](014-image-tiles-are-drawn-from-the-style-along-the-shore.md)), and an archive of their own means a change to them doesn't draw those tiles again.

Over Washington and British Columbia this gives about 125 landmarks, three quarters of them lighthouses.

## Rejected

- **Towers by height alone.** Most broadcast towers have no height in OpenStreetMap, the Mount Constitution ones among them, and a few that do have a wrong one: an observation tower in the woods on Bainbridge Island is tagged 125 m.
- **Every lighthouse and light.** OpenStreetMap has a minor light or beacon on most points and channels; drawn, they would bury the map. Major lights and buildings tagged as lighthouses are the ones people name.
- **Overpass, OpenStreetMap's query service,** instead of extracts. It was too busy to answer on both days this was tried, and a build should not depend on it.

## Known problems

- The Tacoma Narrows Bridge's towers are not in OpenStreetMap as features of their own, so the rule can't find them. The bridge is on the map as a road.
- Charted landmarks include things that change, such as a mast at a marina; they are as current as the extracts.
