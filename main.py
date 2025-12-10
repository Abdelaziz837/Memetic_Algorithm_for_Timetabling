import random as rd
import copy
import time 
import os
import pandas as pd

try:

    df_classrooms = pd.read_csv('classrooms.csv')
    df_courses = pd.read_csv('courses.csv')
    df_instructors = pd.read_csv('instructors.csv')
    df_timeslots = pd.read_csv('timeslots.csv')
    df_students = pd.read_csv('students.csv')
    df_schedule = pd.read_csv('schedule.csv')

except FileNotFoundError:
    print("CSV files Not Found")
    exit()

rooms_lookup = df_classrooms.set_index('classroom_id').to_dict('index')  #creating dictionaries for faster acsess to the data
times_lookup = df_timeslots.set_index('timeslot_id').to_dict('index')
courses_lookup = df_courses.set_index('course_id').to_dict('index')
instructor_lookup = df_instructors.set_index('instructor_id').to_dict('index')

classes_to_scheduale = []

grouped = df_schedule.groupby(['course_id' , 'instructor_id'])

for(course_id , instructor_id) , group in grouped:
    
    student_list = group['student_id'].to_list() #group each course by the student it take then group those students together

    classes_to_scheduale.append({
        'course_id' : course_id , 
        'instructor_id' : instructor_id,
        'students' : set(student_list),        # get the classes needed to be schedualed
        'student_count': len(student_list),
        'course_name' : courses_lookup[course_id]['course_name'],
        'prof_name' :   f"{instructor_lookup[instructor_id]['first_name']}{instructor_lookup[instructor_id]['last_name']}"
    })


print(f"Loaded {len(classes_to_scheduale)} unique classes to schedule.")
print(f"Loaded {len(rooms_lookup)} rooms.")
print(f"Loaded {len(times_lookup)} time slots.")

rooms_id = list(rooms_lookup.keys())

timeslots_id = list(times_lookup.keys())

valid_room_cache = {}

def get_valid_rooms(student_count):
   if student_count in valid_room_cache:
      return valid_room_cache[student_count]
   
   valid = [r_id for r_id , data in rooms_lookup.items() if data['capacity'] >= student_count]

   if not valid :
      valid = [max(rooms_lookup , key=lambda x: rooms_lookup[x]['capacity'])]  #checks to see the student count it it is valid ok if not it sees the next beig room that is big enough for that count
   
   valid_room_cache[student_count] = valid

   return valid



class classgene:

    def __init__(self , class_info):

        self.course_id = class_info['course_id']
        self.instructor_id =  class_info['instructor_id']
        self.students = class_info['students']
        self.student_count =  class_info['student_count']
        self.course_name = class_info['course_name']
        self.prof_name = class_info['prof_name']

        self.valid_room = get_valid_rooms(self.student_count)


        self.room_id = rd.choice(self.valid_room)
        self.timeslot_id = rd.choice(timeslots_id)

        self.is_conflicted = False


    def __repr__(self):
        # This makes it print nicely
     t_data = times_lookup[self.timeslot_id]
     r_data = rooms_lookup[self.room_id]
     conflict_flag = "[!]" if self.is_conflicted else "" # prints !!! if it is a conflicted
     time_str = f"{t_data['day'][:3]} {t_data['start_time']}"
     return f" {conflict_flag}[{self.course_name} | {self.prof_name} | {time_str} | {r_data['room_number']}]"

class ScheduleChromosome:

   def __init__(self , classes_input , empty_init = False):
      
      self.genes = []
      self.fitness = 0
      self.conflicts = 0

      if not empty_init:
            for cls in classes_input:
                self.genes.append(classgene(cls))
            self.getfitness()    


   def __repr__(self):
        return "\n".join([str(gene) for gene in self.genes])

   def getfitness(self):

      conflicts = 0

      for g in self.genes:
         g.is_conflicted = False # resets the conflicted flag to recalculate

      roomusage = {}
      profusage = {}
      studentusage = {}

      for i , gene in enumerate(self.genes):

         roomkey = (gene.timeslot_id , gene.room_id)

         if roomkey in roomusage:

            conflicts += 1
            gene.is_conflicted = True
            self.genes[roomusage[roomkey]].is_conflicted = True

         else:
            roomusage[roomkey]  = i

         profkey = (gene.timeslot_id , gene.instructor_id)

         if profkey in profusage:

            conflicts += 1 
            gene.is_conflicted = True
            self.genes[profusage[profkey]].is_conflicted = True

         else:
            profusage[profkey] = i


         for student in gene.students:
            key = (gene.timeslot_id , student)
            
            if key in studentusage:
               conflicts += 1
               gene.is_conflicted = True
               other_gene = studentusage[key]    #mark this gene (class) as conflicted also mark the other gene (class) that the other student is attending as conflicted
               self.genes[other_gene].is_conflicted = True

            else:
               studentusage[key] = i

      self.conflicts = conflicts
      self.fitness = 1.0 / (1.0 + conflicts)

      return self.fitness
     
def apply_local_search(chromosome : ScheduleChromosome):

   conflicted_indx = [i for i, g in enumerate(chromosome.genes) if g.is_conflicted]

   if not conflicted_indx:
      return
   
   indx = rd.choice(conflicted_indx)

   gene = chromosome.genes[indx]

   current_conflicts = chromosome.conflicts

   original_time = gene.timeslot_id
   original_room = gene.room_id

   best_move_time =  original_time
   best_move_room = original_room

   min_conflict = current_conflicts

   attempts = 0
   while attempts < 20:
      attempts += 1

      newtime = rd.choice(timeslots_id)
      newroom = rd.choice(gene.valid_room)

      if newtime == original_time and newroom == original_room:
         continue

      gene.timeslot_id = newtime
      gene.room_id = newroom

      chromosome.getfitness()

      if chromosome.conflicts < min_conflict:

         min_conflict = chromosome.conflicts
         best_move_time = newtime
         best_move_room = newroom

         break

      gene.timeslot_id = original_time
      gene.room_id = original_room
   
   gene.timeslot_id = best_move_time
   gene.room_id = best_move_room
   chromosome.getfitness()    


def mutate(chromosome : ScheduleChromosome , mutation_rate = 0.1):

   for gene in chromosome.genes:
      
      if gene.is_conflicted:
         effective_rate = 0.5
      else:
         effective_rate = mutation_rate   
      
      if rd.random() < effective_rate:
         
         if rd.random() > 0.5:
             
             gene.room_id = rd.choice(gene.valid_room)
         else:   
             
             gene.timeslot_id = rd.choice(timeslots_id)



def tournament_selection(population , k=5):

   susbet = rd.sample(population , k)

   return max(susbet , key=lambda x:x.fitness)
                

def evolvePopulation(current_pop):

   for chrom in current_pop:
      if chrom.fitness == 0:
         chrom.getfitness()
   
   
   current_pop.sort(key=lambda x:x.fitness , reverse = True)

   apply_local_search(current_pop[0])

   current_pop.sort(key=lambda x:x.fitness , reverse = True)

   # 5. Check for instant victory
   if current_pop[0].fitness == 1.0:
      return current_pop
   

   next_gen = []

   popsize = len(current_pop)

   elite = int(popsize * 0.05)

   for i in range(elite):  #keep tenth of the population

      next_gen.append(copy.deepcopy(current_pop[i]))



   while len(next_gen) < popsize:

      parent_a = tournament_selection(current_pop)
      
      parent_b = tournament_selection(current_pop)

      child = ScheduleChromosome([] ,empty_init=True)

      for i in range(len(parent_a.genes)):

         if rd.random() > 0.5:
            child.genes.append(copy.deepcopy(parent_a.genes[i]))
         else:
            child.genes.append(copy.deepcopy(parent_b.genes[i]))

      mutate(child , 0.05)

      child.getfitness()

      next_gen.append(child)


   return next_gen   

      

def print_generations(population , gen_num):

   os.system('cls' if os.name == 'nt' else 'clear')

   best = population[0]

   print(f"\n{'=' * 80}")
   print(f" GENERATION {gen_num} REPORT | Population Size: {len(population)} | Best fitness : {best.fitness :.4f}")
   print(f"{'='*80}")
   print(f"Conflicts : {best.conflicts}")
   print("-" * 80)
   
   for i in range(min(3 , len(population))):
      
      chrom = population[i]

      print(f"Rank #{i+1} (Conflicts: {chrom.conflicts})")
        # Print first 3 genes as preview
      preview = " | ".join([str(g) for g in chrom.genes[:3]]) 
      print(f"   Sample: {preview}...")
      print("-" * 80)



if __name__ == "__main__":

   pop_size = 100
   max_gens = 500

   print("<<<Initiating population>>>")

   population = [ScheduleChromosome(classes_to_scheduale) for _ in range(pop_size)]

   for gen in range(1 , max_gens + 1):

      population = evolvePopulation(population)

      print_generations(population,gen)

      best = population[0]

      if best.fitness == 1.0:

         print("\n>>> SUCCESS: Perfect Schedule Found! <<<")

         output_data = []
         for gene in best.genes:
                output_data.append({
                    'course_id': gene.course_id,
                    'instructor_id': gene.instructor_id,
                    'room_id': gene.room_id,
                    'timeslot_id': gene.timeslot_id,
                    'course_name': gene.course_name,
                    'room_number': rooms_lookup[gene.room_id]['room_number'],
                    'day': times_lookup[gene.timeslot_id]['day'],
                    'time': times_lookup[gene.timeslot_id]['start_time']
                })
            
         df_out = pd.DataFrame(output_data)
         df_out.to_csv("optimized_schedule.csv", index=False)
         print("Schedule saved to 'optimized_schedule.csv'")
         break


      

   if population[0].fitness < 1.0:
        print("Max generations reached without a perfect schedule.")
        print("NO SCHEDULE WAS FOUND <IMPOSSIBLE TASK>")