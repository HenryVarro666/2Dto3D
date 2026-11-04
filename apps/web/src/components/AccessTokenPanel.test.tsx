import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { AccessTokenPanel } from "./AccessTokenPanel";
import { I18nProvider } from "../i18n";
import { reportUnauthorized } from "../core/auth";
import { fakeApi } from "../test/fixtures";

function mount(api = fakeApi()) {
  return render(
    <I18nProvider>
      <AccessTokenPanel api={api} />
    </I18nProvider>,
  );
}

it("stays invisible on an open server", async () => {
  mount();
  await waitFor(() =>
    expect(screen.queryByLabelText("此服务需要访问令牌")).toBeNull(),
  );
  expect(screen.queryByText("已通过访问令牌登录")).toBeNull();
});

it("asks for the token when the server requires one and signs in with a cookie session", async () => {
  const createSession = vi.fn(async (token: string) => {
    if (token !== "correct-token")
      throw new Error("The access token is not valid.");
    return { required: true, authenticated: true };
  });
  const api = fakeApi({
    getSession: async () => ({ required: true, authenticated: false }),
    createSession,
  });
  mount(api);
  const user = userEvent.setup();
  const input = await screen.findByLabelText("此服务需要访问令牌");
  expect(screen.getByRole("button", { name: "登录" })).toBeDisabled();
  await user.type(input, "wrong");
  await user.click(screen.getByRole("button", { name: "登录" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("访问令牌无效");
  await user.clear(input);
  await user.type(input, "correct-token");
  await user.click(screen.getByRole("button", { name: "登录" }));
  expect(await screen.findByText("已通过访问令牌登录")).toBeInTheDocument();
  expect(createSession).toHaveBeenLastCalledWith("correct-token");
  expect(input).not.toBeInTheDocument();
});

it("reappears when any later request is rejected with 401", async () => {
  mount(
    fakeApi({
      getSession: async () => ({ required: true, authenticated: true }),
    }),
  );
  expect(await screen.findByText("已通过访问令牌登录")).toBeInTheDocument();
  reportUnauthorized();
  expect(
    await screen.findByLabelText("此服务需要访问令牌"),
  ).toBeInTheDocument();
});
