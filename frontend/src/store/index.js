import { configureStore } from "@reduxjs/toolkit";
import complaintReducer from "./slices/complaintSlice";

export const store = configureStore({
  reducer: {
    complaint: complaintReducer,
  },
});
