import React, { createContext, useContext, useState, useEffect } from "react";
import hat_classic from "./assets/hat_classic.png";
import hat_scholar from "./assets/hat_scholar.png";
import hat_strategist from "./assets/hat_strategist.png";

const DolmaAvatarContext = createContext(null);

export const HAT_LIBRARY = {
  hat_classic: {
    id: "hat_classic",
    name: "Classic Top Hat",
    src: hat_classic,
  },
  hat_scholar: {
    id: "hat_scholar",
    name: "Scholar Cap",
    src: hat_scholar,
  },
  hat_strategist: {
    id: "hat_strategist",
    name: "Strategist Hat",
    src: hat_strategist,
  },
};

const STORAGE_KEY = "dolma:selected-hat";

export function DolmaAvatarProvider({ children }) {
  const [selectedHat, setSelectedHat] = useState("hat_classic");

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && HAT_LIBRARY[saved]) setSelectedHat(saved);
  }, []);

  const changeHat = (hatId) => {
    if (HAT_LIBRARY[hatId]) {
      setSelectedHat(hatId);
      localStorage.setItem(STORAGE_KEY, hatId);
    }
  };

  return (
    <DolmaAvatarContext.Provider
      value={{
        selectedHat,
        changeHat,
        hatImage: HAT_LIBRARY[selectedHat].src,
        hats: HAT_LIBRARY,
      }}
    >
      {children}
    </DolmaAvatarContext.Provider>
  );
}

export function useDolmaAvatar() {
  const ctx = useContext(DolmaAvatarContext);
  if (!ctx)
    throw new Error("useDolmaAvatar must be used within DolmaAvatarProvider");
  return ctx;
}
