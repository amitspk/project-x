import { useEffect, useState } from 'react';

type Serializer<T> = {
  read: (value: string | null) => T;
  write: (value: T) => string;
};

const defaultSerializer = <T,>(): Serializer<T | null> => ({
  read: (value) => (value ? (JSON.parse(value) as T) : null),
  write: (value) => JSON.stringify(value)
});

export function useLocalStorage<T>(
  key: string,
  initialValue: T,
  serializer: Serializer<T | null> = defaultSerializer<T>()
): [T, (value: T) => void, () => void] {
  const [stored, setStored] = useState<T>(initialValue);

  useEffect(() => {
    try {
      const item = window.localStorage.getItem(key);
      if (item !== null) {
        const parsed = serializer.read(item);
        if (parsed !== null) {
          setStored(parsed as T);
        }
      } else {
        window.localStorage.setItem(key, serializer.write(initialValue));
      }
    } catch (error) {
      console.warn(`Unable to read localStorage key "${key}":`, error);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const setValue = (value: T) => {
    try {
      setStored(value);
      window.localStorage.setItem(key, serializer.write(value));
    } catch (error) {
      console.warn(`Unable to set localStorage key "${key}":`, error);
    }
  };

  const clear = () => {
    try {
      window.localStorage.removeItem(key);
    } catch (error) {
      console.warn(`Unable to clear localStorage key "${key}":`, error);
    }
    setStored(initialValue);
  };

  return [stored, setValue, clear];
}
