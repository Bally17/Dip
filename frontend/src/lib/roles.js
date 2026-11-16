// Čo ktorá rola smie. Server to vynucuje sám, tu sa podľa toho len skrývajú prvky rozhrania.
const LABELS = { admin: "admin", researcher: "výskumník", member: "člen" };
const RIGHTS = {
  manageUsers: ["admin"],
  eraseParticipant: ["admin"],
  pairDevice: ["member"],
  eraseOwnData: ["member"],
};

export const roleLabel = (role) => LABELS[role] ?? role;
export const can = (role, right) => (RIGHTS[right] ?? []).includes(role);
