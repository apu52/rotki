<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import {
  Blockchain,
  type BlockchainSelection
} from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import { type Module } from '@/types/modules';

const props = defineProps<{ module: Module }>();

const { module } = toRefs(props);
const loading = ref(false);
const selectedAccounts: Ref<GeneralAccount[]> = ref([]);
const { t } = useI18n();
const ETH = Blockchain.ETH;

const store = useQueriedAddressesStore();
const { queriedAddresses } = storeToRefs(store);
const { addQueriedAddress, deleteQueriedAddress } = store;

const { accounts } = useAccountBalances();

const setSelectedAccounts = (addresses: string[]): void => {
  const selected = get(accounts).filter(
    account => account.chain === ETH && addresses.includes(account.address)
  );
  set(selectedAccounts, selected);
};

const added = async (accounts: GeneralAccount<BlockchainSelection>[]) => {
  if (!Array.isArray(accounts)) {
    return;
  }
  set(loading, true);
  const selectedModule = get(module);
  const addresses = accounts.map(({ address }) => address);
  const allAddresses = get(selectedAccounts).map(({ address }) => address);
  const added = addresses.filter(address => !allAddresses.includes(address));
  const removed = allAddresses.filter(address => !addresses.includes(address));

  if (added.length > 0) {
    for (const address of added) {
      await addQueriedAddress({
        address,
        module: selectedModule
      });
    }
  } else if (removed.length > 0) {
    for (const address of removed) {
      await deleteQueriedAddress({
        address,
        module: selectedModule
      });
    }
  }

  setSelectedAccounts(addresses);
  set(loading, false);
};

watch(queriedAddresses, queried => {
  const selectedModule = get(module);
  const queriedForModule = queried[selectedModule];
  setSelectedAccounts(queriedForModule ? queriedForModule : []);
});
</script>

<template>
  <BlockchainAccountSelector
    no-padding
    outlined
    :value="selectedAccounts"
    flat
    :label="t('common.select_address')"
    multiple
    :chains="[ETH]"
    :loading="loading"
    @input="added($event)"
  />
</template>
