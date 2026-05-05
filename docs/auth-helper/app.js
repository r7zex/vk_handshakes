const profileInput = document.querySelector("#vk-profile");
const authUserIdInput = document.querySelector("#auth-user-id");
const tokenPreviewInput = document.querySelector("#token-preview");
const saveButton = document.querySelector("#save-profile");
const clearButton = document.querySelector("#clear");

function maskToken(token) {
  if (!token || token.length < 12) return "";
  return `${token.slice(0, 8)}...${token.slice(-4)}`;
}

function readOAuthFragment() {
  const raw = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const params = new URLSearchParams(raw);
  return {
    accessToken: params.get("access_token"),
    userId: params.get("user_id"),
  };
}

function hydrate() {
  profileInput.value = window.localStorage.getItem("vk_handshakes_profile") || "";

  const oauth = readOAuthFragment();
  if (oauth.userId) {
    authUserIdInput.value = oauth.userId;
    window.localStorage.setItem("vk_handshakes_auth_user_id", oauth.userId);
  } else {
    authUserIdInput.value =
      window.localStorage.getItem("vk_handshakes_auth_user_id") || "";
  }

  if (oauth.accessToken) {
    // Token stays in this browser only. Do not send it anywhere from GitHub Pages.
    window.sessionStorage.setItem("vk_handshakes_access_token", oauth.accessToken);
    tokenPreviewInput.value = maskToken(oauth.accessToken);
    window.history.replaceState(null, "", window.location.pathname);
  } else {
    tokenPreviewInput.value = maskToken(
      window.sessionStorage.getItem("vk_handshakes_access_token")
    );
  }
}

saveButton.addEventListener("click", () => {
  window.localStorage.setItem("vk_handshakes_profile", profileInput.value.trim());
});

clearButton.addEventListener("click", () => {
  window.localStorage.removeItem("vk_handshakes_profile");
  window.localStorage.removeItem("vk_handshakes_auth_user_id");
  window.sessionStorage.removeItem("vk_handshakes_access_token");
  profileInput.value = "";
  authUserIdInput.value = "";
  tokenPreviewInput.value = "";
});

hydrate();
