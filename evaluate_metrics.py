import sys
import argparse

def parse_pubtator_entities_and_relations(filepath):
    """
    Parses a PubTator format file and returns:
    - docs: dict of doc_id -> text
    - entities: dict of doc_id -> list of entity dictionaries with ID and offsets
    - relations: set of (doc_id, e1, e2) where e1 < e2
    """
    docs = {}
    entities = {}
    relations = set()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.find('|t|') != -1:
                doc_id, text = line.split('|t|', 1)
                docs[doc_id] = text
            elif line.find('|a|') != -1:
                pass
            else:
                parts = line.split('\t')
                if len(parts) >= 6 and len(parts) != 4:  # An entity line (doc_id, start, end, text, type, id)
                    doc_id = parts[0]
                    start = int(parts[1])
                    end = int(parts[2])
                    ent_id = parts[5]
                    if doc_id not in entities:
                        entities[doc_id] = []
                    entities[doc_id].append({'id': ent_id, 'start': start, 'end': end})
                elif len(parts) >= 4:  # A relation line (doc_id, class, e1, e2)
                    doc_id = parts[0]
                    rel_class = parts[1]
                    e1 = parts[2]
                    e2 = parts[3]
                    e1_norm, e2_norm = min(e1, e2), max(e1, e2)
                    # We store the relation class instead of just the tuple
                    relations.add((doc_id, e1_norm, e2_norm, rel_class))
                    
    return docs, entities, relations

def get_candidates(entities):
    """
    Returns the set of all possible pairs of entities within each document.
    Filters out pairs of entities that overlap in character offsets.
    """
    candidates = set()
    for doc_id, ent_list in entities.items():
        for i in range(len(ent_list)):
            for j in range(i+1, len(ent_list)):
                ent1 = ent_list[i]
                ent2 = ent_list[j]
                
                if ent1['id'] != ent2['id']:
                    e1, e2 = min(ent1['id'], ent2['id']), max(ent1['id'], ent2['id'])
                    candidates.add((doc_id, e1, e2))
    return candidates

def get_candidates_from_tsv(tsv_file):
    """
    Returns the set of all possible pairs of entities extracted from a TSV file.
    """
    candidates = set()
    with open(tsv_file, 'r', encoding='utf-8') as f:
        header = f.readline()
        if not header.startswith('pmid'):
            f.seek(0)
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 5:
                doc_id = parts[0]
                e1 = parts[3]
                e2 = parts[4]
                e1_norm, e2_norm = min(e1, e2), max(e1, e2)
                candidates.add((doc_id, e1_norm, e2_norm))
    return candidates

def calculate_metrics(pred_file, gold_file, tsv_file=None):
    _, pred_ents, pred_rels = parse_pubtator_entities_and_relations(pred_file)
    _, gold_ents, gold_rels = parse_pubtator_entities_and_relations(gold_file)
    
    if tsv_file:
        all_candidates = get_candidates_from_tsv(tsv_file)
    else:
        gold_candidates = get_candidates(gold_ents)
        pred_candidates = get_candidates(pred_ents)
        # We use all candidates from both gold and pred (though they should match)
        all_candidates = gold_candidates.union(pred_candidates)
    
    from collections import defaultdict

    pred_rels_dict = {(r[0], r[1], r[2]): r[3] for r in pred_rels}
    gold_rels_dict = {(r[0], r[1], r[2]): r[3] for r in gold_rels}

    # Filter out None if present in both, although technically None is the lack of relation.
    # We consider classes in the gold standard and predicted set.
    classes = set(pred_rels_dict.values()).union(set(gold_rels_dict.values()))
    
    # Are we in binary or multiclass? 
    # Usually binary has 'Association' and potentially 'None' (implied by not being in dict).
    # If len(classes) == 1 and list(classes)[0] == 'Association', it's binary.
    # To be safe, we determine based on the number of actual relation classes (excluding None).
    rel_classes = set(c for c in classes if c != "None")
    
    if len(rel_classes) == 1:
        # --- BINARY CLASSIFICATION ---
        pos_class = list(rel_classes)[0]
        print(f"--- BINARY CLASSIFICATION ({pos_class} vs None) ---")
        TP = 0
        FP = 0
        FN = 0
        TN = 0
        
        for cand in all_candidates:
            pred_class = pred_rels_dict.get(cand, "None")
            gold_class = gold_rels_dict.get(cand, "None")
            
            in_pred = (pred_class == pos_class)
            in_gold = (gold_class == pos_class)
            
            if in_pred and in_gold:
                TP += 1
            elif in_pred and not in_gold:
                FP += 1
            elif not in_pred and in_gold:
                FN += 1
            else:
                TN += 1
                
        print(f"Total pairs (N): {len(all_candidates)}")
        print(f"TP (Positive pairs): {TP}")
        print(f"FP (Predicted positive but negative): {FP}")
        print(f"FN (Predicted negative but positive): {FN}")
        print(f"TN (Negative pairs): {TN}\n")
        
        # Accuracy
        accuracy = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0.0
        print(f"Accuracy: {accuracy:.4f}\n")
        
        # Positive class (P) metrics
        precision_P = TP / (TP + FP) if (TP + FP) > 0 else 0.0
        recall_P = TP / (TP + FN) if (TP + FN) > 0 else 0.0
        f1_P = (2 * precision_P * recall_P) / (precision_P + recall_P) if (precision_P + recall_P) > 0 else 0.0
        
        print(f"Precision (Positive): {precision_P:.4f}")
        print(f"Recall (Positive):    {recall_P:.4f}")
        print(f"F1 (Positive):        {f1_P:.4f}\n")
        
        # Negative class (N) metrics
        precision_N = TN / (TN + FN) if (TN + FN) > 0 else 0.0
        recall_N = TN / (TN + FP) if (TN + FP) > 0 else 0.0
        f1_N = (2 * precision_N * recall_N) / (precision_N + recall_N) if (precision_N + recall_N) > 0 else 0.0
        
        print(f"Precision (Negative): {precision_N:.4f}")
        print(f"Recall (Negative):    {recall_N:.4f}")
        print(f"F1 (Negative):        {f1_N:.4f}\n")
        
        # Micro F1
        n_P = TP + FN # number of actual positives
        n_N = TN + FP # number of actual negatives
        N = len(all_candidates)
        micro_f1 = (n_P / N) * f1_P + (n_N / N) * f1_N if N > 0 else 0.0
        print(f"Micro F1: {micro_f1:.4f}")
        
        # Macro F1
        macro_f1 = (f1_P + f1_N) / 2.0
        print(f"Macro F1: {macro_f1:.4f}")

    else:
        # --- MULTI-CLASS CLASSIFICATION ---
        print(f"--- MULTI-CLASS CLASSIFICATION ---")
        Overall_Correct = 0
        Total_Samples = len(all_candidates)
        print(f"Total pairs (N): {Total_Samples}\n")

        # First pass for Accuracy
        for cand in all_candidates:
            pred_class = pred_rels_dict.get(cand, "None")
            gold_class = gold_rels_dict.get(cand, "None")
            if pred_class == gold_class:
                Overall_Correct += 1
                
        accuracy = Overall_Correct / Total_Samples if Total_Samples > 0 else 0.0
        print(f"Accuracy: {accuracy:.4f}\n")

        class_metrics = {}
        for c in classes:
            TP_i = 0
            FP_i = 0
            FN_i = 0
            
            for cand in all_candidates:
                pred_class = pred_rels_dict.get(cand, "None")
                gold_class = gold_rels_dict.get(cand, "None")
                
                if pred_class == c and gold_class == c:
                    TP_i += 1
                elif pred_class == c and gold_class != c:
                    FP_i += 1
                elif pred_class != c and gold_class == c:
                    FN_i += 1
                    
            precision_i = TP_i / (TP_i + FP_i) if (TP_i + FP_i) > 0 else 0.0
            recall_i = TP_i / (TP_i + FN_i) if (TP_i + FN_i) > 0 else 0.0
            f1_i = (2 * precision_i * recall_i) / (precision_i + recall_i) if (precision_i + recall_i) > 0 else 0.0
            
            n_i = TP_i + FN_i # actual samples in class i
            
            class_metrics[c] = {
                'TP': TP_i, 'FP': FP_i, 'FN': FN_i,
                'Precision': precision_i, 'Recall': recall_i, 'F1': f1_i,
                'n_i': n_i
            }
            
            print(f"--- Class: {c} ---")
            print(f"TP: {TP_i}, FP: {FP_i}, FN: {FN_i}")
            print(f"n_i (Actual samples): {n_i}")
            print(f"Precision: {precision_i:.4f}")
            print(f"Recall:    {recall_i:.4f}")
            print(f"F1:        {f1_i:.4f}\n")
            
        # Micro F1 (average weighted by class support)
        micro_f1 = 0.0
        for c, metrics in class_metrics.items():
            micro_f1 += (metrics['n_i'] / Total_Samples) * metrics['F1']
            
        # Macro F1 (simple average across classes)
        macro_f1 = sum([m['F1'] for m in class_metrics.values()]) / len(classes) if len(classes) > 0 else 0.0
        
        print(f"--- Overall Metrics ---")
        print(f"Micro F1 (Weighted by support): {micro_f1:.4f}")
        print(f"Macro F1 (Simple average):      {macro_f1:.4f}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Evaluate Relation Extraction on AIMed pubtator files")
    parser.add_argument('--pred_file', required=True, help="Path to predictions pubtator file")
    parser.add_argument('--gold_file', required=True, help="Path to ground truth pubtator file")
    parser.add_argument('--candidate_tsv', required=False, help="Optional path to TSV file to filter exact evaluated candidates")
    args = parser.parse_args()
    
    calculate_metrics(args.pred_file, args.gold_file, args.candidate_tsv)
