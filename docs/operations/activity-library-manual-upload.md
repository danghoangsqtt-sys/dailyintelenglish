# Activity Library — manual picture names

Open **Shot Library → Activity Library → Add activity pictures**. Choose Generic,
Alex or Lina, then select one or more 16:9 PNG, JPEG or WebP pictures (at least
640×360). Enter a short English **activity name for each picture**. The app does
not analyze the image or infer a name.

The name, optional context tags and optional alternative phrases are visible as
soon as the dialog opens. You can enter the first picture's details before
choosing files; after selecting multiple pictures, the dialog shows a separate
set of fields for each file, displaying one picture and its fields at a time.
Click a numbered thumbnail or use **Previous** / **Next** to switch pictures;
the large preview and fields always change together. The footer shows how many
pictures have names. **Add pictures** becomes available when every selected
file has a name.

Use the action a script would say, for example `go east`, `go west`, `turn left`,
`cook dinner` or `stretch`. Optional **alternative phrases** help a storyboard
match other wording (`head east`, `walk east` for `go east`). Optional context tags
describe the setting in the library; the current video matcher relies on the
activity name and alternative phrases.

Press **Add pictures**. Each picture starts at **Needs review**. Check its name,
scope and aliases in **Preview / edit**, then **Approve** it. Only approved
pictures are available to the automatic video matcher. Renaming an existing
picture does not change its review state; previously imported pictures can be
corrected in the same editor.

Each card also has **Delete**. Confirming it removes that picture from the
library and deletes its stored file. If the picture was used before, its library
usage history is removed as well; already rendered videos keep their output,
while future renders cannot select the deleted picture.

To act on specific pictures together, tick **Select** on each card. Use **Select
all in view** for the current filters, then choose **Approve selected**, **Reject
selected**, or **Delete selected**. The confirmation shows how many pictures will
change. Pictures already in the chosen review state are skipped. Changing a
filter clears the selection so hidden pictures are never changed by surprise.
If a request fails partway through, the message shows how many finished and
keeps the remaining pictures selected for retry. Deletion also warns when a
selected picture has been used in a render.

To review a prepared set faster, filter the Activity Library to the intended
scope and **Needs review**, check the visible names, then press **Approve pending
in view**. The confirmation shows how many pictures will become available to
videos. This action changes only pending pictures shown by the current filters;
it does not infer or correct their names. Pictures with incorrect names should
be edited before bulk approval.

For prepared collections, the **Advanced: import a prepared folder** control
still reads owner-written names from filenames such as
`generic__go-east__city__01.png` in `data/library/activities_inbox`.

The two older compass examples previously labelled `walking outdoors` remain
pending. Review them and enter `go east` and `go west` (plus suitable aliases)
before approving them for video use.
