import { afterEach, describe, expect, it, vi } from "vitest";
import { analyzeFile } from "./api";

describe("file analysis request", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends a selected file as multipart data", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ modality: "pdf" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await analyzeFile(
      new File(["synthetic placeholder"], "synthetic.pdf", {
        type: "application/pdf",
      }),
    );

    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("http://localhost:8000/api/analyze/file");
    expect(init?.method).toBe("POST");
    expect(init?.headers).toBeUndefined();
    expect(init?.body).toBeInstanceOf(FormData);
    if (!(init?.body instanceof FormData)) {
      throw new Error("File analysis request must use multipart form data.");
    }

    const uploaded = init.body.get("file");
    expect(uploaded).toBeInstanceOf(File);
    if (!(uploaded instanceof File)) {
      throw new Error("File analysis request must include the selected file.");
    }
    expect(uploaded.name).toBe("synthetic.pdf");
    expect(uploaded.type).toBe("application/pdf");
  });
});
