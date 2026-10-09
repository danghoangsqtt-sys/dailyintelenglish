# Activity Library image manifest

Store generated images in these three folders. The importer now scans their files
recursively, so do not move approved assets elsewhere before importing.

- `data/library/activities_inbox/alex/`
- `data/library/activities_inbox/lina/`
- `data/library/activities_inbox/generic/`

Use the exact filename below. Each filename has the form
`scope__activity__context__variant.png`; keep the double underscores and use
variant `01` for the first accepted image. If you create a distinct valid
alternative for the same activity, increment only the final variant, for example
`alex__cooking__kitchen__02.png`.

| Activity | Alex folder | Lina folder | Generic folder |
| --- | --- | --- | --- |
| Exercise | `alex/alex__exercise__morning__01.png` | `lina/lina__exercise__morning__01.png` | `generic/generic__exercise__morning__01.png` |
| Walking | `alex/alex__walking__outdoors__01.png` | `lina/lina__walking__outdoors__01.png` | `generic/generic__walking__outdoors__01.png` |
| Jogging / running | `alex/alex__jogging__outdoors__01.png` | `lina/lina__jogging__outdoors__01.png` | `generic/generic__jogging__outdoors__01.png` |
| Cycling | `alex/alex__cycling__outdoors__01.png` | `lina/lina__cycling__outdoors__01.png` | `generic/generic__cycling__outdoors__01.png` |
| Cooking | `alex/alex__cooking__kitchen__01.png` | `lina/lina__cooking__kitchen__01.png` | `generic/generic__cooking__kitchen__01.png` |
| Baking | `alex/alex__baking__kitchen__01.png` | `lina/lina__baking__kitchen__01.png` | `generic/generic__baking__kitchen__01.png` |
| Eating | `alex/alex__eating__cafe__01.png` | `lina/lina__eating__cafe__01.png` | `generic/generic__eating__cafe__01.png` |
| Drinking coffee / tea | `alex/alex__drinking-coffee__cafe__01.png` | `lina/lina__drinking-coffee__cafe__01.png` | `generic/generic__drinking-coffee__cafe__01.png` |
| Grocery shopping | `alex/alex__grocery-shopping__store__01.png` | `lina/lina__grocery-shopping__store__01.png` | `generic/generic__grocery-shopping__store__01.png` |
| Cleaning | `alex/alex__cleaning__home__01.png` | `lina/lina__cleaning__home__01.png` | `generic/generic__cleaning__home__01.png` |
| Gardening | `alex/alex__gardening__balcony__01.png` | `lina/lina__gardening__balcony__01.png` | `generic/generic__gardening__balcony__01.png` |
| Reading | `alex/alex__reading__library__01.png` | `lina/lina__reading__library__01.png` | `generic/generic__reading__library__01.png` |
| Studying / writing notes | `alex/alex__studying__desk__01.png` | `lina/lina__studying__desk__01.png` | `generic/generic__studying__desk__01.png` |
| Laptop work | `alex/alex__laptop-work__home-office__01.png` | `lina/lina__laptop-work__home-office__01.png` | `generic/generic__laptop-work__home-office__01.png` |
| Meeting / presentation | `alex/alex__meeting__office__01.png` | `lina/lina__meeting__office__01.png` | `generic/generic__meeting__office__01.png` |
| Commuting by train | `alex/alex__commuting__train__01.png` | `lina/lina__commuting__train__01.png` | `generic/generic__commuting__train__01.png` |
| Driving | `alex/alex__driving__city__01.png` | `lina/lina__driving__city__01.png` | `generic/generic__driving__city__01.png` |
| Packing for travel | `alex/alex__packing__bedroom__01.png` | `lina/lina__packing__bedroom__01.png` | `generic/generic__packing__bedroom__01.png` |
| Relaxing / listening to music | `alex/alex__relaxing__living-room__01.png` | `lina/lina__relaxing__living-room__01.png` | `generic/generic__relaxing__living-room__01.png` |
| Morning routine | `alex/alex__morning-routine__bedroom__01.png` | `lina/lina__morning-routine__bedroom__01.png` | `generic/generic__morning-routine__bedroom__01.png` |
| Brushing teeth | `alex/alex__brushing-teeth__bathroom__01.png` | `lina/lina__brushing-teeth__bathroom__01.png` | `generic/generic__brushing-teeth__bathroom__01.png` |
| Doing laundry | `alex/alex__doing-laundry__laundry-room__01.png` | `lina/lina__doing-laundry__laundry-room__01.png` | `generic/generic__doing-laundry__laundry-room__01.png` |
| Shopping for clothes | `alex/alex__shopping-for-clothes__clothing-store__01.png` | `lina/lina__shopping-for-clothes__clothing-store__01.png` | `generic/generic__shopping-for-clothes__clothing-store__01.png` |
| Working out at the gym | `alex/alex__working-out__gym__01.png` | `lina/lina__working-out__gym__01.png` | `generic/generic__working-out__gym__01.png` |
| Taking photos outdoors | `alex/alex__taking-photos__outdoors__01.png` | `lina/lina__taking-photos__outdoors__01.png` | `generic/generic__taking-photos__outdoors__01.png` |

## Import checklist

1. Store each image in its indicated scope folder, not directly in
   `activities_inbox`.
2. Ensure it is a normal, non-transparent PNG/JPEG/WebP, 16:9, and at least
   640x360.
3. Import it from Shot Library, inspect the detected activity/context, then
   approve it before it can be matched in a render.
4. For a file that must remain out of matching, import it but leave its review
   state as pending or reject it.
