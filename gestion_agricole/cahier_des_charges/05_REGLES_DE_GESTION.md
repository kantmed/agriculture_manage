# RÈGLES DE GESTION

## Module `gestion_agricole` — Odoo 20 Community

### 1. RÈGLES TRANSVERSALES

- **Multi-société** : chaque enregistrement appartient à une société. Les
  utilisateurs ne voient que les données de leurs sociétés.
- **Multi-exploitation** : une société peut gérer plusieurs exploitations.
- **Unités de mesure** : toutes les quantités sont exprimées dans des unités
  cohérentes (superficie en hectares, volumes en litres, poids en kg).
- **Dates et périodes** : les campagnes sont définies par des dates de début
  et de fin. Les opérations sont datées.
- **Historique** : toute modification importante est tracée (utilisateur, date).
- **Archivage** : les enregistrements inactifs sont archivés, pas supprimés.
- **Traçabilité** : les intrants utilisés sont tracés par lot.
- **Cohérence** : les coûts sont calculés à partir des données réelles.
- **Erreurs de saisie** : les validations empêchent les saisies incohérentes.
- **Restrictions d'accès** : chaque profil dispose des droits nécessaires.
- **Numérotation** : les documents sont numérotés automatiquement.
- **États et transitions** : les enregistrements suivent des cycles de vie
  définis (brouillon → validé → clôturé).

### 2. RÈGLES SPÉCIFIQUES

- Une parcelle ne peut pas être affectée à deux cultures simultanément.
- Un code de référentiel global est réservé à toutes les sociétés.
- Un code de société ne peut pas entrer en conflit avec un code global.
- Les références archivées libèrent leur code et leur nom.
- Les coûts sont calculés par parcelle, culture et campagne.

---

*Rédigé dans le cadre du Prompt N°36 — Module `gestion_agricole` — Odoo 20 Community.*
