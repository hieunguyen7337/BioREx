import json
from collections import defaultdict

import argparse

def main():
    parser = argparse.ArgumentParser(description="Convert Phos dataset JSON to PubTator format")
    parser.add_argument('--input_file', required=True, help="Path to input Phos JSON Lines file")
    parser.add_argument('--output_file', required=True, help="Path to output PubTator file")
    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file

    documents = defaultdict(list)

    # Read JSON Lines file
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print("Error decoding json line:", line[:100])
                continue
            
            import hashlib
            # Formatting ID similar to previous script but adaptable
            base_id = str(item.get('id', 'unknown'))
            # Format base_id if possible
            doc_id = base_id.replace('.', '_').replace('_s', '_')
            text_hash = hashlib.md5(item['text'].encode('utf-8')).hexdigest()[:6]
            doc_id = f"{doc_id}_{text_hash}"
            documents[doc_id].append(item)

    print(f"Loaded {len(documents)} unique documents/sentences.")

    # Process each document and write to PubTator format
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for doc_id, items in documents.items():
            # All items for a doc_id have the same text
            text = items[0]['text']
            out_f.write(f"{doc_id}|t|{text}\n")
            
            entities = {}
            t_id_counter = 1
            relations = []
            
            for item in items:
                for rel in item.get('relation', []):
                    e1_idx = rel['entity_1_idx']
                    e2_idx = rel['entity_2_idx']
                    
                    # Extract positions
                    e1_start = e1_idx[0][0]
                    e1_end = e1_idx[-1][1]
                    e2_start = e2_idx[0][0]
                    e2_end = e2_idx[-1][1]
                    
                    # Validate bounds: if entity offsets exceed document text, it means 
                    # the entity belongs to another sentence in the original full document.
                    # We skip these out-of-bounds cross-sentence entities.
                    if e1_start < 0 or e1_end > len(text) or e2_start < 0 or e2_end > len(text):
                        continue
                    
                    # Use strictly sliced text to bypass dirty markers like '[/E1]' in JSON
                    e1_text = text[e1_start:e1_end]
                    e1_key = (e1_start, e1_end)
                    
                    # For phosphorylation corpus, entity types might be 'protein', let's use what the json says if available, else gene
                    e1_type = rel.get('entity_1_type', 'Gene')
                    e2_type = rel.get('entity_2_type', 'Gene')

                    if e1_key not in entities:
                        entities[e1_key] = {
                            'text': e1_text,
                            'type': e1_type,
                            't_id': f"T{t_id_counter}"
                        }
                        t_id_counter += 1
                    
                    e2_text = text[e2_start:e2_end]
                    e2_key = (e2_start, e2_end)
                    
                    if e2_key not in entities:
                        entities[e2_key] = {
                            'text': e2_text,
                            'type': e2_type,
                            't_id': f"T{t_id_counter}"
                        }
                        t_id_counter += 1
                    
                    # Record relations
                    # Record PPI relations with the correct type
                    rel_type = rel.get('BioREx_relation_type', 'Association')
                    relations.append((entities[e1_key]['t_id'], entities[e2_key]['t_id'], rel_type))
            
            # Write entities sorted by start offset
            for key in sorted(entities.keys()):
                start, end = key
                ent = entities[key]
                out_f.write(f"{doc_id}\t{start}\t{end}\t{ent['text']}\t{ent['type']}\t{ent['t_id']}\n")
                
            # Write unique relations
            unique_relations = []
            for r in relations:
                if r not in unique_relations:
                    unique_relations.append(r)
                    
            for r in unique_relations:
                out_f.write(f"{doc_id}\t{r[2]}\t{r[0]}\t{r[1]}\n")
                
            # Blank line separates documents in PubTator format
            out_f.write("\n")

    print(f"Conversion complete. Output saved to {output_file}")


if __name__ == "__main__":
    main()
