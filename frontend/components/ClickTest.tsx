"use client";

export function ClickTest() {
  return (
    <button
      type="button"
      onClick={() => alert("client js works")}
      className="fixed bottom-4 right-4 z-50 rounded bg-red-500 px-4 py-2 text-white"
    >
      Test Click
    </button>
  );
}
