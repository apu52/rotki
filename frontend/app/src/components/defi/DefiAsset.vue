<script setup lang="ts">
import { type DefiAsset } from '@/types/defi/overview';
import { createEvmIdentifierFromAddress } from '@/utils/assets';

const props = defineProps<{
  asset: DefiAsset;
}>();

const { asset } = toRefs(props);

const evmIdentifier: ComputedRef<string> = computed(() =>
  createEvmIdentifierFromAddress(get(asset).tokenAddress)
);
</script>

<template>
  <div class="flex items-center py-4">
    <AssetIcon size="32px" :identifier="evmIdentifier" />
    <span class="ml-3">{{ asset.tokenSymbol }}</span>
    <VSpacer />
    <div class="flex flex-col items-end">
      <BalanceDisplay no-icon :asset="evmIdentifier" :value="asset.balance" />
    </div>
  </div>
</template>
