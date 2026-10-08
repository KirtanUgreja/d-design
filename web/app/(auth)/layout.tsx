import { Placard } from "@/components/placard";
import { SlideThumb } from "@/components/slide-thumb";
import { asset, loadRecording, recordingIds } from "@/lib/fixtures";

// Sign in and sign up: the form on one side, real output on the other, hung
// like prints on a wall. Nothing on the wall is a mock-up.
export default async function AuthLayout({ children }: { children: React.ReactNode }) {
  const covers = [];
  for (const id of await recordingIds()) {
    const r = await loadRecording(id);
    const thumb = r.ok ? r.value.slides[0]?.thumb : undefined;
    if (r.ok && thumb) covers.push({ id, src: asset(id, thumb), thesis: r.value.thesis });
  }
  return (
    <main className="mx-auto grid max-w-[1440px] gap-16 px-4 py-12 sm:px-8 lg:min-h-[calc(100dvh-57px)] lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-center lg:py-0">
      <div className="w-full max-w-sm">{children}</div>
      {covers.length >= 3 && (
        <figure aria-hidden="true" className="hidden min-w-0 lg:block">
          <div className="grid grid-cols-2 gap-6">
            <div className="col-span-2">
              <SlideThumb src={covers[0]?.src ?? ""} alt="" />
            </div>
            {covers.slice(1, 3).map((c) => (
              <div key={c.id}>
                <SlideThumb src={c.src} alt="" />
              </div>
            ))}
          </div>
          <Placard label="Made from one-line briefs" aside="Every slide checked in a browser" className="mt-4" />
        </figure>
      )}
    </main>
  );
}
