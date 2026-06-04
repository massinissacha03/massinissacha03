"""
Script de comparaison de fichiers CSV
Compare un fichier prod.csv avec un fichier salesforce.csv
Détecte les différences ligne par ligne en utilisant une clé unique
"""

import csv
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FieldDifference:
    """Représente une différence pour un champ spécifique"""
    field_name: str
    prod_value: str
    salesforce_value: str


@dataclass
class RecordDifference:
    """Représente toutes les différences pour un enregistrement"""
    record_id: str
    differences: List[FieldDifference]


class CSVComparator:
    """Classe pour comparer deux fichiers CSV"""
    
    def __init__(self, prod_file: str, salesforce_file: str, 
                 id_column: str = "Id", ignored_fields: Set[str] = None):
        """
        Initialise le comparateur
        
        Args:
            prod_file: Chemin du fichier prod.csv
            salesforce_file: Chemin du fichier salesforce.csv
            id_column: Nom de la colonne contenant la clé unique
            ignored_fields: Ensemble des colonnes à ignorer dans la comparaison
        """
        self.prod_file = prod_file
        self.salesforce_file = salesforce_file
        self.id_column = id_column
        self.ignored_fields = ignored_fields or set()
        self.differences: List[RecordDifference] = []
        
    def _read_csv_file(self, filepath: str) -> Dict[str, Dict[str, str]]:
        """
        Lit un fichier CSV et retourne un dictionnaire indexé par la clé unique
        
        Args:
            filepath: Chemin du fichier CSV
            
        Returns:
            Dictionnaire {id: {field: value}}
        """
        data = {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                if reader.fieldnames is None:
                    print(f"⚠️  Erreur: Le fichier {filepath} est vide ou mal formé")
                    return data
                
                for row in reader:
                    # Vérifier que la clé unique existe
                    if self.id_column not in row:
                        print(f"⚠️  Attention: Colonne '{self.id_column}' introuvable dans {filepath}")
                        continue
                    
                    record_id = row[self.id_column]
                    if record_id:  # Ignorer les lignes avec une clé vide
                        data[record_id] = row
                    else:
                        print(f"⚠️  Attention: Clé unique vide trouvée dans {filepath}")
                        
        except FileNotFoundError:
            print(f"❌ Erreur: Le fichier {filepath} n'existe pas")
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {filepath}: {e}")
            
        return data
    
    def _normalize_value(self, value: str) -> str:
        """
        Normalise une valeur pour la comparaison
        Gère les valeurs None/vides
        
        Args:
            value: Valeur à normaliser
            
        Returns:
            Valeur normalisée
        """
        if value is None or value == "":
            return "[VIDE]"
        return str(value).strip()
    
    def compare(self) -> List[RecordDifference]:
        """
        Compare les deux fichiers CSV
        
        Returns:
            Liste des différences trouvées
        """
        print("📂 Lecture des fichiers CSV...")
        prod_data = self._read_csv_file(self.prod_file)
        salesforce_data = self._read_csv_file(self.salesforce_file)
        
        print(f"✓ {self.prod_file}: {len(prod_data)} enregistrements")
        print(f"✓ {self.salesforce_file}: {len(salesforce_data)} enregistrements")
        
        # Récupérer toutes les clés uniques des deux fichiers
        all_ids = set(prod_data.keys()) | set(salesforce_data.keys())
        
        print(f"\n🔍 Comparaison de {len(all_ids)} enregistrements...")
        
        self.differences = []
        
        for record_id in sorted(all_ids):
            prod_row = prod_data.get(record_id, {})
            sf_row = salesforce_data.get(record_id, {})
            
            # Récupérer toutes les colonnes communes (ignorer les colonnes absentes)
            prod_columns = set(prod_row.keys()) if prod_row else set()
            sf_columns = set(sf_row.keys()) if sf_row else set()
            common_columns = prod_columns & sf_columns
            
            # Filtrer les colonnes à ignorer
            common_columns = common_columns - self.ignored_fields - {self.id_column}
            
            # Détecter les différences
            field_differences = []
            for field in sorted(common_columns):
                prod_value = self._normalize_value(prod_row.get(field, ""))
                sf_value = self._normalize_value(sf_row.get(field, ""))
                
                if prod_value != sf_value:
                    field_differences.append(
                        FieldDifference(
                            field_name=field,
                            prod_value=prod_value,
                            salesforce_value=sf_value
                        )
                    )
            
            # Ajouter à la liste si des différences ont été trouvées
            if field_differences:
                self.differences.append(
                    RecordDifference(
                        record_id=record_id,
                        differences=field_differences
                    )
                )
        
        return self.differences
    
    def print_report(self):
        """Affiche un rapport lisible des différences"""
        if not self.differences:
            print("\n✅ Aucune différence trouvée!")
            return
        
        print(f"\n{'='*80}")
        print(f"📊 RAPPORT DE COMPARAISON - {len(self.differences)} enregistrement(s) différent(s)")
        print(f"{'='*80}\n")
        
        for record_diff in self.differences:
            print(f"📌 Enregistrement ID: {record_diff.record_id}")
            print(f"   {len(record_diff.differences)} différence(s) détectée(s)")
            print(f"   {'-'*76}")
            
            for diff in record_diff.differences:
                print(f"   • Champ: {diff.field_name}")
                print(f"     ├─ PROD:       {diff.prod_value}")
                print(f"     └─ Salesforce: {diff.salesforce_value}")
            
            print()
    
    def export_to_csv(self, output_file: str = "diff.csv"):
        """
        Exporte les différences dans un fichier CSV
        
        Args:
            output_file: Chemin du fichier de sortie
        """
        if not self.differences:
            print("ℹ️  Aucune différence à exporter")
            return
        
        try:
            fieldnames = ["Id", "Champ", "Valeur_PROD", "Valeur_Salesforce"]
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for record_diff in self.differences:
                    for diff in record_diff.differences:
                        writer.writerow({
                            "Id": record_diff.record_id,
                            "Champ": diff.field_name,
                            "Valeur_PROD": diff.prod_value,
                            "Valeur_Salesforce": diff.salesforce_value
                        })
            
            print(f"✅ Fichier '{output_file}' généré avec succès")
            print(f"   ({len(self.differences)} enregistrement(s), "
                  f"{sum(len(d.differences) for d in self.differences)} différence(s) totale(s))")
            
        except Exception as e:
            print(f"❌ Erreur lors de l'export: {e}")
    
    def get_statistics(self) -> Dict:
        """
        Retourne des statistiques sur les différences
        
        Returns:
            Dictionnaire avec les statistiques
        """
        total_differences = sum(len(d.differences) for d in self.differences)
        field_stats = {}
        
        for record_diff in self.differences:
            for diff in record_diff.differences:
                field_stats[diff.field_name] = field_stats.get(diff.field_name, 0) + 1
        
        return {
            "total_records_with_differences": len(self.differences),
            "total_field_differences": total_differences,
            "fields_with_differences": field_stats,
            "most_different_field": max(field_stats, key=field_stats.get) if field_stats else None
        }


def main():
    """Fonction principale - Exemple d'utilisation"""
    
    # ==========================================
    # Configuration
    # ==========================================
    prod_file = "prod.csv"
    salesforce_file = "salesforce.csv"
    id_column = "Id"  # Changez selon votre clé unique
    
    # Colonnes à ignorer (ex: timestamps, champs techniques)
    ignored_fields = {
        "LastModifiedDate",
        "CreatedDate",
        "SystemModstamp",
        "LastModifiedById",
        "CreatedById"
    }
    
    # ==========================================
    # Comparaison
    # ==========================================
    comparator = CSVComparator(
        prod_file=prod_file,
        salesforce_file=salesforce_file,
        id_column=id_column,
        ignored_fields=ignored_fields
    )
    
    # Effectuer la comparaison
    differences = comparator.compare()
    
    # Afficher le rapport
    comparator.print_report()
    
    # Afficher les statistiques
    stats = comparator.get_statistics()
    if stats["total_records_with_differences"] > 0:
        print(f"{'='*80}")
        print(f"📈 STATISTIQUES")
        print(f"{'='*80}")
        print(f"• Enregistrements avec différences: {stats['total_records_with_differences']}")
        print(f"• Nombre total de différences: {stats['total_field_differences']}")
        print(f"• Champ le plus différent: {stats['most_different_field']}")
        print(f"\nDécomposition par champ:")
        for field, count in sorted(stats["fields_with_differences"].items(), key=lambda x: x[1], reverse=True):
            print(f"   • {field}: {count} différence(s)")
        print()
    
    # Exporter les différences
    comparator.export_to_csv("diff.csv")


if __name__ == "__main__":
    main()
