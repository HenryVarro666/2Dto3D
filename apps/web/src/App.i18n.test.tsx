// Preload the real viewer before timed UI waits; cold transforms can exceed 1s on CI.
import "./components/SceneViewer";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import App from "./App";
import { completed, fakeApi, result, running } from "./test/fixtures";
import type { JobInput } from "./api/types";

const languageLabel = "语言 / Language / Idioma";
const photo = new File(["image"], "field-inverter.png", { type: "image/png" });

it("switches the workspace, controls and document language between Chinese, English and Spanish", async () => {
  const user = userEvent.setup();
  render(<App apiClient={fakeApi()} />);
  const selector = screen.getByRole("combobox", { name: languageLabel });
  expect(selector).toHaveValue("zh");
  await user.selectOptions(selector, "en");
  expect(
    screen.getByRole("heading", { name: "Equipment Structure Workbench" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Choose photo" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("progressbar", { name: "Processing stage progress" }),
  ).toHaveAttribute("aria-valuenow", "0");
  expect(document.documentElement.lang).toBe("en");
  await user.selectOptions(selector, "es");
  expect(
    screen.getByRole("heading", { name: "Mesa de trabajo de estructuras" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Elegir foto" }),
  ).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("es");
  await user.selectOptions(selector, "zh");
  expect(
    screen.getByRole("heading", { name: "设备结构工作台" }),
  ).toBeInTheDocument();
  expect(document.documentElement.lang).toBe("zh-CN");
});

it("restores the last chosen language when the workspace is opened again", async () => {
  const user = userEvent.setup();
  const view = render(<App apiClient={fakeApi()} />);
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "es",
  );
  view.unmount();
  render(<App apiClient={fakeApi()} />);
  expect(screen.getByRole("combobox", { name: languageLabel })).toHaveValue(
    "es",
  );
  expect(
    screen.getByRole("heading", { name: "Mesa de trabajo de estructuras" }),
  ).toBeInTheDocument();
});

it("changes the language of an in-flight stage without starting recognition again", async () => {
  const user = userEvent.setup();
  let jobs = 0;
  const job = { ...running, stage: "loading_segmentation" };
  render(
    <App
      apiClient={fakeApi({
        createJob: async () => {
          jobs += 1;
          return job;
        },
        getJob: async () => job,
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await screen.findByText("正在载入区域分割模型");
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "en",
  );
  expect(
    screen.getByText("Loading the segmentation model"),
  ).toBeInTheDocument();
  expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "3");
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "es",
  );
  expect(
    screen.getByText("Cargando el modelo de segmentación"),
  ).toBeInTheDocument();
  expect(screen.getByText("field-inverter.png")).toBeInTheDocument();
  expect(jobs).toBe(1);
});

it("localizes built-in component names but keeps edits, visibility and submitted component data", async () => {
  const user = userEvent.setup();
  let submitted: JobInput | undefined;
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) => {
          if (input.mode === "manual") submitted = input;
          return completed;
        },
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "en",
  );
  await user.click(
    screen.getByRole("button", { name: "Edit Inverter cabinet" }),
  );
  const name = screen.getByRole("textbox", { name: "Component name" });
  expect(name).toHaveValue("Inverter cabinet");
  await user.clear(name);
  await user.type(name, "CAB-A / 现场柜");
  await user.click(
    screen.getByRole("checkbox", { name: "Show CAB-A / 现场柜" }),
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "es",
  );
  expect(
    screen.getByRole("textbox", { name: "Nombre del componente" }),
  ).toHaveValue("CAB-A / 现场柜");
  expect(
    screen.getByRole("checkbox", { name: "Mostrar CAB-A / 现场柜" }),
  ).not.toBeChecked();
  await user.click(
    screen.getByRole("button", { name: "Regenerar estructura" }),
  );
  expect(submitted?.components?.[0].label).toBe("CAB-A / 现场柜");
  expect(submitted?.components?.[1].label).toBe(result.components[1].label);
  expect(submitted?.components?.map((item) => item.id)).toEqual([
    "cabinet-1",
    "bracket-2",
  ]);
});

it("translates a stored API error when the language changes", async () => {
  const user = userEvent.setup();
  render(
    <App
      apiClient={fakeApi({
        uploadAsset: async () => {
          throw new Error("The upload exceeds 20 MB.");
        },
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "es",
  );
  expect(screen.getByRole("alert")).toHaveTextContent(
    "La foto supera el límite de 20 MB.",
  );
});

it("preserves an explicitly edited default name through a rebuild and language changes", async () => {
  const user = userEvent.setup();
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) =>
          input.mode === "manual"
            ? {
                ...completed,
                id: "manual-name",
                result: {
                  ...result,
                  job_id: "manual-name",
                  scene_url: "/api/jobs/manual-name/scene.glb",
                },
              }
            : completed,
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "en",
  );
  await user.click(
    screen.getByRole("button", { name: "Edit Inverter cabinet" }),
  );
  const name = screen.getByRole("textbox", { name: "Component name" });
  await user.clear(name);
  await user.type(name, "逆变器机柜");
  expect(name).toHaveValue("逆变器机柜");
  await user.click(
    screen.getByRole("button", { name: "Regenerate structure" }),
  );
  await waitFor(() => expect(name).toBeEnabled());
  expect(name).toHaveValue("逆变器机柜");
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "es",
  );
  expect(
    screen.getByRole("textbox", { name: "Nombre del componente" }),
  ).toHaveValue("逆变器机柜");
});

it("keeps system names localized when only the category changes, including after regeneration", async () => {
  const user = userEvent.setup();
  render(
    <App
      apiClient={fakeApi({
        createJob: async (input) =>
          input.mode === "manual"
            ? {
                ...completed,
                id: "manual-category",
                result: {
                  ...result,
                  job_id: "manual-category",
                  scene_url: "/api/jobs/manual-category/scene.glb",
                  components: result.components.map((component, index) =>
                    index === 0
                      ? {
                          ...component,
                          category: "bracket",
                          source: "manual",
                          score: null,
                        }
                      : component,
                  ),
                },
              }
            : completed,
      })}
    />,
  );
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "重新生成结构" })).toBeEnabled(),
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "en",
  );
  await user.click(
    screen.getByRole("button", { name: "Edit Inverter cabinet" }),
  );
  const name = screen.getByRole("textbox", { name: "Component name" });
  await user.selectOptions(
    screen.getByRole("combobox", { name: "Component category" }),
    "bracket",
  );
  expect(name).toHaveValue("Inverter cabinet");
  await user.click(
    screen.getByRole("button", { name: "Regenerate structure" }),
  );
  await waitFor(() => expect(name).toBeEnabled());
  expect(name).toHaveValue("Inverter cabinet");
});

it("localizes a task interrupted by a service restart", async () => {
  const user = userEvent.setup();
  render(
    <App
      apiClient={fakeApi({
        createJob: async () => ({
          ...running,
          status: "interrupted",
          stage: "interrupted",
          error:
            "The server stopped before this task finished. Start a new task to try again.",
        }),
      })}
    />,
  );
  await user.selectOptions(
    screen.getByRole("combobox", { name: languageLabel }),
    "es",
  );
  await user.upload(screen.getByLabelText("Elegir foto del equipo"), photo);
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "La tarea se interrumpió al reiniciar el servicio.",
  );
});

it("displays connector and cable-tray categories in all three languages without changing IDs", async () => {
  const user = userEvent.setup();
  const components = [
    { ...result.components[0], id: "plug-1", category: "connector" as const, label: "接线插接件" },
    { ...result.components[0], id: "tray-1", category: "cable_tray" as const, label: "电缆线槽" },
  ];
  render(<App apiClient={fakeApi({
    createJob: async () => ({ ...completed, result: { ...result, components } }),
  })} />);
  await user.upload(screen.getByLabelText("选择设备照片"), photo);
  expect(await screen.findByRole("button", { name: "选择 接线插接件" })).toBeInTheDocument();
  const selector = screen.getByRole("combobox", { name: languageLabel });
  await user.selectOptions(selector, "en");
  expect(screen.getByRole("button", { name: "Select Electrical connector" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Select Cable tray" })).toBeInTheDocument();
  await user.selectOptions(selector, "es");
  expect(screen.getByRole("button", { name: "Seleccionar Conector eléctrico" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Seleccionar Canaleta de cables" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Editar Conector eléctrico" }));
  expect(screen.getByText("plug-1")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Editar Canaleta de cables" }));
  expect(screen.getByText("tray-1")).toBeInTheDocument();
});
