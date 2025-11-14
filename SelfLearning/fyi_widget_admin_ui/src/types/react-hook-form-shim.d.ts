import type { FieldValues, UseFormProps, UseFormReturn } from 'react-hook-form/dist/types';

declare module 'react-hook-form' {
  export function useForm<
    TFieldValues extends FieldValues = FieldValues,
    TContext = any,
    TTransformedValues = TFieldValues
  >(
    props?: UseFormProps<TFieldValues, TContext, TTransformedValues>
  ): UseFormReturn<TFieldValues, TContext, TTransformedValues>;
}
