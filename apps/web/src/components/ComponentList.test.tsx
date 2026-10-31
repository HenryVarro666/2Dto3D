import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { useState } from "react";
import { ComponentList } from "./ComponentList";
import { cabinet, bracket } from "../test/fixtures";

it("links component selection, visibility, isolation, and editing while preserving the component ID", async () => {
  const user = userEvent.setup();
  function WorkbenchHarness() {
    const [selected, setSelected] = useState<string | null>(null);
    const [hidden, setHidden] = useState<Set<string>>(new Set());
    const [components, setComponents] = useState([cabinet, bracket]);
    return (
      <ComponentList
        components={components}
        selectedId={selected}
        hiddenIds={hidden}
        onSelect={setSelected}
        onToggle={(id) =>
          setHidden((current) => {
            const next = new Set(current);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
          })
        }
        onIsolate={(id) =>
          setHidden(
            new Set(
              components
                .filter((item) => item.id !== id)
                .map((item) => item.id),
            ),
          )
        }
        onChange={(id, patch) =>
          setComponents((current) =>
            current.map((item) =>
              item.id === id ? { ...item, ...patch } : item,
            ),
          )
        }
        onRemove={(id) =>
          setComponents((current) => current.filter((item) => item.id !== id))
        }
      />
    );
  }
  render(<WorkbenchHarness />);
  await user.click(screen.getByRole("button", { name: "选择 安装支架" }));
  expect(screen.getByRole("button", { name: "选择 安装支架" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await user.click(screen.getByRole("checkbox", { name: "显示 逆变器机柜" }));
  expect(
    screen.getByRole("checkbox", { name: "显示 逆变器机柜" }),
  ).not.toBeChecked();
  await user.click(screen.getByRole("button", { name: "只看 安装支架" }));
  expect(screen.getByRole("checkbox", { name: "显示 安装支架" })).toBeChecked();
  await user.click(screen.getByRole("button", { name: "编辑 安装支架" }));
  const input = screen.getByRole("textbox", { name: "组件名称" });
  await user.clear(input);
  await user.type(input, "外部支架");
  expect(
    screen.getByRole("button", { name: "选择 外部支架" }),
  ).toBeInTheDocument();
  expect(screen.getByText("bracket-2")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "移除组件" }));
  expect(
    screen.queryByRole("button", { name: "选择 外部支架" }),
  ).not.toBeInTheDocument();
});
