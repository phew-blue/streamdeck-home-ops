// plugin/src/paint.ts
//
// Keep what a key should be showing, and put it back when Stream Deck forgets.
//
// Stream Deck does not persist an image set by a plugin. Whenever it redraws a
// key from the profile -- switching page, opening the app, waking the device --
// the key reverts to the default declared in the plugin's manifest, which here
// is a green dot. The plugin only repainted when it polled, and the cluster
// tiles poll every five minutes, so they showed the default nearly all the time
// and the real artwork for a moment after each fetch.
//
// So the last title and image for each key are remembered and reapplied on a
// short timer. The values are already in hand and the artwork is cached, so a
// repaint costs one websocket message and no work.

/** How often to put the artwork back. Comfortably inside a glance. */
const REPAINT_MS = 5_000;

interface Face {
  title: string;
  image: string;
}

interface Target {
  setTitle(t: string): Promise<void>;
  setImage(i: string): Promise<void>;
}

const faces = new Map<string, Face>();
const timers = new Map<string, ReturnType<typeof setInterval>>();

/** Draw a key now, and remember it so it can be drawn again. */
export async function paint(id: string, act: Target, title: string, image: string): Promise<void> {
  faces.set(id, { title, image });
  await act.setTitle(title);
  await act.setImage(image);
}

/**
 * Start repainting a key until it disappears.
 *
 * Safe to call more than once for the same key: a second call replaces the
 * first timer rather than adding one.
 */
export function keepPainted(id: string, act: Target): void {
  stopPainting(id);
  timers.set(id, setInterval(() => {
    const face = faces.get(id);
    if (!face) return;
    // Fire and forget: a failed repaint is retried in five seconds anyway, and
    // throwing inside a timer would take the plugin down.
    void act.setTitle(face.title).catch(() => {});
    void act.setImage(face.image).catch(() => {});
  }, REPAINT_MS));
}

/** Stop repainting, and forget the key. */
export function stopPainting(id: string): void {
  const t = timers.get(id);
  if (t) {
    clearInterval(t);
    timers.delete(id);
  }
  faces.delete(id);
}
